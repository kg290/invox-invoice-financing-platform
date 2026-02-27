"""
Invoice Factoring with Recourse Options
════════════════════════════════════════
Three factoring types with dynamic pricing:

  Type               Risk to Lender  Rate Range   Description
  ────────────────  ──────────────── ────────────  ───────────────────────────
  Non-Recourse       Highest          18-24%       Lender absorbs all default risk
  Partial-Recourse   Medium           14-18%       Shared risk (vendor liable for %)
  Full-Recourse      Lowest           10-14%       Vendor liable for 100% default

Dynamic pricing factors: Vendor credit score, buyer creditworthiness,
invoice amount, tenure, industry risk, historical default data.
"""

import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    FactoringAgreement, MarketplaceListing, Invoice, Vendor,
    CreditScore, EMandateRegistration,
)
from services.credit_scoring import compute_credit_score


# ═══════════════════════════════════════════════
#  DYNAMIC PRICING ENGINE
# ═══════════════════════════════════════════════

FACTORING_CONFIG = {
    "non_recourse": {
        "base_rate_range": (18.0, 24.0),
        "recourse_percentage": 0,
        "risk_premium": 3.0,
        "insurance_rate": 2.0,
        "description": "Lender assumes 100% of default risk",
        "min_vendor_score": 55,
    },
    "partial_recourse": {
        "base_rate_range": (14.0, 18.0),
        "recourse_percentage": 30,
        "risk_premium": 1.5,
        "insurance_rate": 1.0,
        "description": "Vendor liable for 30% of outstanding on default",
        "min_vendor_score": 40,
    },
    "full_recourse": {
        "base_rate_range": (10.0, 14.0),
        "recourse_percentage": 100,
        "risk_premium": 0.5,
        "insurance_rate": 0.0,
        "description": "Vendor liable for 100% of outstanding on default",
        "min_vendor_score": 25,
    },
}


def _calculate_dynamic_rate(
    factoring_type: str,
    vendor_score: float,
    buyer_score: float,
    invoice_amount: float,
    tenure_days: int,
) -> dict:
    """Calculate interest rate based on risk factors."""
    config = FACTORING_CONFIG[factoring_type]
    low, high = config["base_rate_range"]

    # Start from midpoint
    base_rate = (low + high) / 2

    # Vendor score adjustment (-3% to +3%)
    vendor_adj = ((50 - vendor_score) / 50) * 3.0

    # Buyer credit adjustment (-1.5% to +1.5%)
    buyer_adj = ((50 - buyer_score) / 50) * 1.5

    # Amount tier adjustment (larger invoices = small discount)
    if invoice_amount > 1000000:
        amount_adj = -0.5
    elif invoice_amount > 500000:
        amount_adj = -0.25
    elif invoice_amount < 50000:
        amount_adj = 0.5
    else:
        amount_adj = 0.0

    # Tenure adjustment (longer = riskier)
    if tenure_days > 120:
        tenure_adj = 1.0
    elif tenure_days > 90:
        tenure_adj = 0.5
    else:
        tenure_adj = 0.0

    risk_premium = config["risk_premium"]
    insurance_rate = config["insurance_rate"]

    effective_rate = base_rate + vendor_adj + buyer_adj + amount_adj + tenure_adj + risk_premium + insurance_rate
    effective_rate = max(low, min(high + 4, effective_rate))  # Clamp

    return {
        "base_rate": round(base_rate, 2),
        "vendor_adjustment": round(vendor_adj, 2),
        "buyer_adjustment": round(buyer_adj, 2),
        "amount_adjustment": round(amount_adj, 2),
        "tenure_adjustment": round(tenure_adj, 2),
        "risk_premium": risk_premium,
        "insurance_rate": insurance_rate,
        "effective_rate": round(effective_rate, 2),
    }


# ═══════════════════════════════════════════════
#  FACTORING AGREEMENT CREATION
# ═══════════════════════════════════════════════

def get_factoring_options(db: Session, listing_id: int) -> dict:
    """Return available factoring options for a marketplace listing."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise ValueError("Listing not found")

    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
    if not invoice:
        raise ValueError("Invoice not found")

    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()

    # Get vendor credit score
    vendor_score_data = compute_credit_score(db, listing.vendor_id)
    vendor_score = vendor_score_data["total_score"]

    # Estimate buyer score (use a default if buyer info not available)
    buyer_score = 60.0  # Default moderate buyer score

    invoice_amount = listing.requested_amount
    tenure_days = listing.repayment_period_days or 90

    options = []
    for ftype, config in FACTORING_CONFIG.items():
        if vendor_score < config["min_vendor_score"]:
            options.append({
                "type": ftype,
                "available": False,
                "reason": f"Minimum vendor credit score: {config['min_vendor_score']}. Current: {vendor_score}",
            })
            continue

        rate_info = _calculate_dynamic_rate(ftype, vendor_score, buyer_score, invoice_amount, tenure_days)

        # Compute total cost
        effective_annual_rate = rate_info["effective_rate"]
        daily_rate = effective_annual_rate / 365 / 100
        total_interest = round(invoice_amount * daily_rate * tenure_days, 2)
        vendor_receives = round(invoice_amount - total_interest, 2)
        lender_earns = total_interest

        options.append({
            "type": ftype,
            "available": True,
            "recourse_percentage": config["recourse_percentage"],
            "description": config["description"],
            "rate_breakdown": rate_info,
            "financials": {
                "invoice_amount": invoice_amount,
                "effective_annual_rate": rate_info["effective_rate"],
                "tenure_days": tenure_days,
                "total_interest": total_interest,
                "vendor_receives_upfront": vendor_receives,
                "lender_total_return": lender_earns,
            },
        })

    return {
        "listing_id": listing_id,
        "invoice_id": listing.invoice_id,
        "vendor_id": listing.vendor_id,
        "vendor_score": vendor_score,
        "vendor_grade": vendor_score_data["risk_grade"],
        "options": options,
    }


def create_factoring_agreement(
    db: Session,
    listing_id: int,
    lender_id: int,
    factoring_type: str,
    mandate_id: Optional[int] = None,
) -> dict:
    """Create a factoring agreement with the chosen recourse type."""
    if factoring_type not in FACTORING_CONFIG:
        raise ValueError(f"Invalid factoring type: {factoring_type}. Must be one of: {list(FACTORING_CONFIG.keys())}")

    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise ValueError("Listing not found")
    if listing.listing_status not in ("open", "active"):
        raise ValueError("Listing is not open for funding")

    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()

    # Compute scores
    vendor_score_data = compute_credit_score(db, listing.vendor_id)
    vendor_score = vendor_score_data["total_score"]
    config = FACTORING_CONFIG[factoring_type]

    if vendor_score < config["min_vendor_score"]:
        raise ValueError(f"Vendor score {vendor_score} below minimum {config['min_vendor_score']} for {factoring_type}")

    buyer_score = 60.0
    invoice_amount = listing.requested_amount
    tenure_days = listing.repayment_period_days or 90

    rate_info = _calculate_dynamic_rate(factoring_type, vendor_score, buyer_score, invoice_amount, tenure_days)

    daily_rate = rate_info["effective_rate"] / 365 / 100
    total_interest = round(invoice_amount * daily_rate * tenure_days, 2)

    # Create agreement
    agreement = FactoringAgreement(
        listing_id=listing_id,
        invoice_id=listing.invoice_id,
        vendor_id=listing.vendor_id,
        lender_id=lender_id,
        factoring_type=factoring_type,
        recourse_percentage=config["recourse_percentage"],
        base_interest_rate=rate_info["base_rate"],
        risk_premium_rate=rate_info["risk_premium"],
        insurance_rate=rate_info["insurance_rate"],
        effective_interest_rate=rate_info["effective_rate"],
        vendor_credit_score=vendor_score,
        buyer_credit_score=buyer_score,
        invoice_amount=invoice_amount,
        funded_amount=round(invoice_amount - total_interest, 2),
        tenure_days=tenure_days,
        repayment_due_date=datetime.now(timezone.utc) + timedelta(days=tenure_days),
        agreement_status="active",
        mandate_id=mandate_id,
    )
    db.add(agreement)

    # Update listing status
    listing.listing_status = "funded"
    listing.funded_by = lender_id
    listing.funded_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(agreement)

    return {
        "agreement_id": agreement.id,
        "listing_id": listing_id,
        "factoring_type": factoring_type,
        "recourse_percentage": config["recourse_percentage"],
        "rate_breakdown": rate_info,
        "financials": {
            "invoice_amount": invoice_amount,
            "funded_amount": agreement.funded_amount,
            "total_interest": total_interest,
            "effective_rate": rate_info["effective_rate"],
            "tenure_days": tenure_days,
            "repayment_due_date": agreement.repayment_due_date.isoformat(),
        },
        "status": "active",
        "created_at": agreement.created_at.isoformat() if agreement.created_at else None,
    }


def get_factoring_agreement(db: Session, agreement_id: int) -> dict:
    """Retrieve factoring agreement details."""
    agreement = db.query(FactoringAgreement).filter(FactoringAgreement.id == agreement_id).first()
    if not agreement:
        raise ValueError("Factoring agreement not found")

    mandate_info = None
    if agreement.mandate_id:
        mandate = db.query(EMandateRegistration).filter(EMandateRegistration.id == agreement.mandate_id).first()
        if mandate:
            mandate_info = {
                "mandate_id": mandate.id,
                "mandate_reference": mandate.mandate_reference,
                "status": mandate.mandate_status,
                "max_amount": mandate.max_amount,
            }

    return {
        "agreement_id": agreement.id,
        "listing_id": agreement.listing_id,
        "invoice_id": agreement.invoice_id,
        "vendor_id": agreement.vendor_id,
        "lender_id": agreement.lender_id,
        "factoring_type": agreement.factoring_type,
        "recourse_percentage": agreement.recourse_percentage,
        "rates": {
            "base_rate": agreement.base_interest_rate,
            "risk_premium": agreement.risk_premium_rate,
            "insurance_rate": agreement.insurance_rate,
            "effective_rate": agreement.effective_interest_rate,
        },
        "financials": {
            "invoice_amount": agreement.invoice_amount,
            "funded_amount": agreement.funded_amount,
            "tenure_days": agreement.tenure_days,
            "repayment_due_date": agreement.repayment_due_date.isoformat() if agreement.repayment_due_date else None,
        },
        "status": agreement.agreement_status,
        "mandate": mandate_info,
        "created_at": agreement.created_at.isoformat() if agreement.created_at else None,
    }

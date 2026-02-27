"""
Real-Time Credit Scoring Engine — ML-Based Dynamic Credit Assessment
═══════════════════════════════════════════════════════════════════════
Computes a live credit score (0-100) using multiple data sources:

  Component                Weight   Source
  ─────────────────────── ────── ──────────────────────
  CIBIL Score               25%   TransUnion CIBIL
  GST Compliance            20%   GST Portal / WhiteBooks
  Platform Repayment        20%   InvoX transaction data
  Bank Account Health       15%   Account Aggregator sim
  Invoice Quality           10%   Invoice pattern analysis
  Business Stability        10%   Age + employees + turnover

Output: Score, Risk Grade, Interest Rate, Max Funding, Confidence
"""

import json
import math
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from models import (
    Vendor, Invoice, MarketplaceListing, RepaymentSchedule,
    CreditScore, InvoiceVerificationReport, VerificationCheck,
)


# ═══════════════════════════════════════════════
#  RISK GRADE MAPPING
# ═══════════════════════════════════════════════
def _score_to_grade(score: float) -> str:
    if score >= 90: return "AAA"
    if score >= 80: return "AA"
    if score >= 70: return "A"
    if score >= 60: return "BBB"
    if score >= 50: return "BB"
    if score >= 40: return "B"
    if score >= 30: return "C"
    return "D"


def _grade_to_interest_rate(grade: str) -> float:
    """Map risk grade to recommended annual interest rate."""
    rates = {
        "AAA": 8.5, "AA": 10.0, "A": 12.0, "BBB": 14.0,
        "BB": 16.5, "B": 19.0, "C": 22.0, "D": 28.0,
    }
    return rates.get(grade, 20.0)


def _score_to_max_funding_pct(score: float) -> float:
    """Higher score = higher funding percentage of invoice value."""
    if score >= 85: return 85
    if score >= 70: return 80
    if score >= 55: return 75
    if score >= 40: return 70
    return 60


def _score_to_max_tenure(score: float) -> int:
    """Higher score = longer repayment tenure allowed."""
    if score >= 80: return 180
    if score >= 60: return 120
    if score >= 40: return 90
    return 60


# ═══════════════════════════════════════════════
#  COMPONENT 1: CIBIL SCORE (25%)
# ═══════════════════════════════════════════════
def _score_cibil(vendor: Vendor) -> tuple[float, dict]:
    """Convert CIBIL score (300-900) to 0-100 component."""
    cibil = vendor.cibil_score or 0
    if cibil <= 0:
        return 20.0, {"cibil_raw": 0, "note": "No CIBIL data available"}

    # Normalize: 300 → 0, 900 → 100
    normalized = max(0, min(100, ((cibil - 300) / 600) * 100))
    details = {
        "cibil_raw": cibil,
        "normalized_score": round(normalized, 1),
        "range": "Excellent" if cibil >= 750 else "Good" if cibil >= 700 else "Fair" if cibil >= 650 else "Poor" if cibil >= 550 else "Very Poor",
    }
    return round(normalized, 1), details


# ═══════════════════════════════════════════════
#  COMPONENT 2: GST COMPLIANCE (20%)
# ═══════════════════════════════════════════════
def _score_gst_compliance(vendor: Vendor) -> tuple[float, dict]:
    """Score based on GST filing regularity and compliance status."""
    score = 50.0  # Default mid-range
    details = {}

    # Compliance status
    status = (vendor.gst_compliance_status or "").lower()
    if status in ("regular", "compliant"):
        score += 25
        details["compliance_status"] = "Regular (good)"
    elif status == "irregular":
        score -= 15
        details["compliance_status"] = "Irregular (concerning)"
    elif status == "defaulter":
        score -= 40
        details["compliance_status"] = "Defaulter (high risk)"
    else:
        details["compliance_status"] = "Unknown"

    # Filing frequency and count
    total_filings = vendor.total_gst_filings or 0
    years_since_reg = 1
    if vendor.gst_registration_date:
        try:
            reg_date = datetime.strptime(vendor.gst_registration_date, "%Y-%m-%d")
            years_since_reg = max(1, (datetime.now() - reg_date).days / 365)
        except (ValueError, TypeError):
            pass

    expected_filings = years_since_reg * (12 if vendor.gst_filing_frequency == "Monthly" else 4)
    filing_ratio = total_filings / max(1, expected_filings)

    if filing_ratio >= 0.95:
        score += 20
        details["filing_regularity"] = f"Excellent ({total_filings}/{expected_filings:.0f} expected)"
    elif filing_ratio >= 0.8:
        score += 10
        details["filing_regularity"] = f"Good ({total_filings}/{expected_filings:.0f} expected)"
    elif filing_ratio >= 0.5:
        details["filing_regularity"] = f"Fair ({total_filings}/{expected_filings:.0f} expected)"
    else:
        score -= 15
        details["filing_regularity"] = f"Poor ({total_filings}/{expected_filings:.0f} expected)"

    # Turnover declared
    if vendor.annual_turnover and vendor.annual_turnover > 500000:
        score += 5
        details["annual_turnover"] = f"₹{vendor.annual_turnover:,.0f}"

    return round(max(0, min(100, score)), 1), details


# ═══════════════════════════════════════════════
#  COMPONENT 3: PLATFORM REPAYMENT HISTORY (20%)
# ═══════════════════════════════════════════════
def _score_repayment_history(vendor: Vendor, db: Session) -> tuple[float, dict]:
    """Score based on past repayment performance on the platform."""
    listings = db.query(MarketplaceListing).filter(
        MarketplaceListing.vendor_id == vendor.id,
        MarketplaceListing.listing_status.in_(["funded", "settled"]),
    ).all()

    if not listings:
        return 50.0, {"note": "No repayment history (new borrower)", "total_loans": 0}

    listing_ids = [l.id for l in listings]
    all_installments = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.listing_id.in_(listing_ids)
    ).all()

    if not all_installments:
        return 55.0, {"note": "Loan active, no installments due yet", "total_loans": len(listings)}

    total = len(all_installments)
    paid = sum(1 for i in all_installments if i.status == "paid")
    overdue = sum(1 for i in all_installments if i.status == "overdue")
    pending = sum(1 for i in all_installments if i.status == "pending")

    settled = sum(1 for l in listings if l.listing_status == "settled")

    on_time_rate = paid / max(1, total)
    default_rate = overdue / max(1, total)

    score = 50.0
    score += on_time_rate * 40      # Up to +40 for perfect repayment
    score -= default_rate * 50       # Harsh penalty for defaults
    score += min(settled * 5, 15)    # Bonus for settled loans (up to +15)

    details = {
        "total_loans": len(listings),
        "settled_loans": settled,
        "total_installments": total,
        "paid_on_time": paid,
        "overdue": overdue,
        "pending": pending,
        "on_time_rate": f"{on_time_rate:.0%}",
        "default_rate": f"{default_rate:.0%}",
    }

    return round(max(0, min(100, score)), 1), details


# ═══════════════════════════════════════════════
#  COMPONENT 4: BANK ACCOUNT HEALTH (15%)
# ═══════════════════════════════════════════════
def _score_bank_health(vendor: Vendor) -> tuple[float, dict]:
    """
    Score based on bank account indicators.
    In production, would use RBI Account Aggregator APIs.
    Here we simulate using available vendor data.
    """
    score = 50.0
    details = {}

    # Monthly revenue vs liabilities ratio
    monthly_rev = vendor.monthly_revenue or 0
    liabilities = vendor.existing_liabilities or 0
    turnover = vendor.annual_turnover or 0

    if turnover > 0:
        debt_to_income = liabilities / turnover
        if debt_to_income < 0.15:
            score += 30
            details["debt_to_income"] = f"{debt_to_income:.1%} (Excellent)"
        elif debt_to_income < 0.3:
            score += 20
            details["debt_to_income"] = f"{debt_to_income:.1%} (Good)"
        elif debt_to_income < 0.5:
            score += 5
            details["debt_to_income"] = f"{debt_to_income:.1%} (Fair)"
        else:
            score -= 20
            details["debt_to_income"] = f"{debt_to_income:.1%} (High risk)"

    # Business assets as collateral buffer
    assets = vendor.business_assets_value or 0
    if assets > 0 and turnover > 0:
        asset_ratio = assets / turnover
        if asset_ratio > 0.5:
            score += 15
            details["asset_coverage"] = f"{asset_ratio:.1f}x (Strong)"
        elif asset_ratio > 0.2:
            score += 5
            details["asset_coverage"] = f"{asset_ratio:.1f}x (Moderate)"
        else:
            details["asset_coverage"] = f"{asset_ratio:.1f}x (Low)"

    # Monthly revenue consistency indicator
    if monthly_rev > 0 and turnover > 0:
        expected_monthly = turnover / 12
        consistency = monthly_rev / expected_monthly
        if 0.8 <= consistency <= 1.2:
            score += 5
            details["revenue_consistency"] = "Consistent"
        else:
            details["revenue_consistency"] = f"Variance detected ({consistency:.1f}x)"

    details["bank_name"] = vendor.bank_name
    details["bank_ifsc"] = vendor.bank_ifsc

    return round(max(0, min(100, score)), 1), details


# ═══════════════════════════════════════════════
#  COMPONENT 5: INVOICE QUALITY (10%)
# ═══════════════════════════════════════════════
def _score_invoice_quality(vendor: Vendor, db: Session) -> tuple[float, dict]:
    """Score based on invoice quality metrics from platform data."""
    invoices = db.query(Invoice).filter(Invoice.vendor_id == vendor.id).all()

    if not invoices:
        return 50.0, {"note": "No invoices on platform", "total_invoices": 0}

    total = len(invoices)
    paid_invoices = sum(1 for i in invoices if i.payment_status == "paid")
    overdue_invoices = sum(1 for i in invoices if i.invoice_status == "overdue")
    listed = sum(1 for i in invoices if i.is_listed)

    # Check verification reports
    verified_count = db.query(InvoiceVerificationReport).filter(
        InvoiceVerificationReport.vendor_id == vendor.id,
        InvoiceVerificationReport.overall_status == "verified",
    ).count()

    score = 50.0
    if total > 0:
        paid_rate = paid_invoices / total
        score += paid_rate * 20

        if overdue_invoices / total > 0.3:
            score -= 20

        if listed > 0:
            score += min(listed * 2, 15)

        if verified_count > 0:
            verification_rate = verified_count / total
            score += verification_rate * 15

    details = {
        "total_invoices": total,
        "paid_invoices": paid_invoices,
        "overdue_invoices": overdue_invoices,
        "listed_on_marketplace": listed,
        "triple_verified": verified_count,
    }

    return round(max(0, min(100, score)), 1), details


# ═══════════════════════════════════════════════
#  COMPONENT 6: BUSINESS STABILITY (10%)
# ═══════════════════════════════════════════════
def _score_business_stability(vendor: Vendor) -> tuple[float, dict]:
    """Score based on business age, size, and growth indicators."""
    score = 50.0
    details = {}

    # Business age
    current_year = datetime.now().year
    age = current_year - (vendor.year_of_establishment or current_year)
    if age >= 10:
        score += 25
        details["business_age"] = f"{age} years (Well established)"
    elif age >= 5:
        score += 15
        details["business_age"] = f"{age} years (Established)"
    elif age >= 3:
        score += 8
        details["business_age"] = f"{age} years (Growing)"
    elif age >= 1:
        details["business_age"] = f"{age} year(s) (New)"
    else:
        score -= 10
        details["business_age"] = f"{age} years (Very new — higher risk)"

    # Employee count (proxy for business size)
    employees = vendor.number_of_employees or 0
    if employees >= 50:
        score += 10
        details["employee_size"] = f"{employees} (Medium enterprise)"
    elif employees >= 10:
        score += 5
        details["employee_size"] = f"{employees} (Small enterprise)"
    elif employees >= 1:
        details["employee_size"] = f"{employees} (Micro enterprise)"
    else:
        details["employee_size"] = "Unknown"

    # Verification status
    if vendor.profile_status == "verified":
        score += 10
        details["profile_verified"] = True
    else:
        details["profile_verified"] = False

    # Business type
    biz_type = (vendor.business_type or "").lower()
    if biz_type in ("pvt ltd", "llp"):
        score += 5
        details["business_type_bonus"] = "Limited liability entity"
    elif biz_type == "partnership":
        score += 2
    details["business_type"] = vendor.business_type

    return round(max(0, min(100, score)), 1), details


# ═══════════════════════════════════════════════
#  MAIN SCORING ENGINE
# ═══════════════════════════════════════════════

def compute_credit_score(db: Session, vendor_id: int) -> dict:
    """
    Compute real-time credit score for a vendor.
    Returns: score, grade, recommendations, breakdown.
    """
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise ValueError("Vendor not found")

    # Compute all components
    cibil_score, cibil_details = _score_cibil(vendor)
    gst_score, gst_details = _score_gst_compliance(vendor)
    repayment_score, repayment_details = _score_repayment_history(vendor, db)
    bank_score, bank_details = _score_bank_health(vendor)
    invoice_score, invoice_details = _score_invoice_quality(vendor, db)
    stability_score, stability_details = _score_business_stability(vendor)

    # Weighted composite
    total_score = round(
        cibil_score * 0.25 +
        gst_score * 0.20 +
        repayment_score * 0.20 +
        bank_score * 0.15 +
        invoice_score * 0.10 +
        stability_score * 0.10,
        1
    )
    total_score = max(0, min(100, total_score))

    # Derive grade and recommendations
    grade = _score_to_grade(total_score)
    recommended_rate = _grade_to_interest_rate(grade)
    max_funding_pct = _score_to_max_funding_pct(total_score)
    max_tenure = _score_to_max_tenure(total_score)
    max_funding_amount = round(
        (vendor.annual_turnover or 0) * max_funding_pct / 100 * 0.3, 2
    )  # 30% of eligible turnover

    # Confidence level (more data = higher confidence)
    data_points = 0
    if vendor.cibil_score: data_points += 1
    if vendor.total_gst_filings: data_points += 1
    if repayment_details.get("total_loans", 0) > 0: data_points += 1
    if vendor.annual_turnover: data_points += 1
    if invoice_details.get("total_invoices", 0) > 0: data_points += 1
    if vendor.year_of_establishment: data_points += 1
    confidence = min(1.0, data_points / 6)

    # Save to DB
    credit_record = CreditScore(
        vendor_id=vendor_id,
        total_score=total_score,
        risk_grade=grade,
        confidence_level=confidence,
        cibil_component=cibil_score,
        gst_compliance_component=gst_score,
        repayment_history_component=repayment_score,
        bank_health_component=bank_score,
        invoice_quality_component=invoice_score,
        business_stability_component=stability_score,
        recommended_interest_rate=recommended_rate,
        recommended_max_funding=max_funding_amount,
        recommended_max_tenure_days=max_tenure,
        data_snapshot_json=json.dumps({
            "cibil": cibil_details,
            "gst": gst_details,
            "repayment": repayment_details,
            "bank": bank_details,
            "invoice": invoice_details,
            "stability": stability_details,
        }, default=str),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
    )
    db.add(credit_record)

    # Also update vendor risk_score
    vendor.risk_score = round(100 - total_score, 1)  # Invert for risk (100-score)
    db.commit()
    db.refresh(credit_record)

    return {
        "score_id": credit_record.id,
        "vendor_id": vendor_id,
        "total_score": total_score,
        "risk_grade": grade,
        "confidence_level": round(confidence, 2),
        "recommendations": {
            "interest_rate": recommended_rate,
            "max_funding_percentage": max_funding_pct,
            "max_funding_amount": max_funding_amount,
            "max_tenure_days": max_tenure,
        },
        "breakdown": {
            "cibil": {"score": cibil_score, "weight": "25%", "details": cibil_details},
            "gst_compliance": {"score": gst_score, "weight": "20%", "details": gst_details},
            "repayment_history": {"score": repayment_score, "weight": "20%", "details": repayment_details},
            "bank_health": {"score": bank_score, "weight": "15%", "details": bank_details},
            "invoice_quality": {"score": invoice_score, "weight": "10%", "details": invoice_details},
            "business_stability": {"score": stability_score, "weight": "10%", "details": stability_details},
        },
        "scored_at": credit_record.scored_at.isoformat() if credit_record.scored_at else None,
        "valid_until": credit_record.expires_at.isoformat() if credit_record.expires_at else None,
    }


def get_credit_score_history(db: Session, vendor_id: int) -> list[dict]:
    """Get credit score history for trend analysis."""
    scores = db.query(CreditScore).filter(
        CreditScore.vendor_id == vendor_id
    ).order_by(CreditScore.scored_at.desc()).limit(20).all()

    return [{
        "score_id": s.id,
        "total_score": s.total_score,
        "risk_grade": s.risk_grade,
        "confidence_level": s.confidence_level,
        "components": {
            "cibil": s.cibil_component,
            "gst": s.gst_compliance_component,
            "repayment": s.repayment_history_component,
            "bank": s.bank_health_component,
            "invoice": s.invoice_quality_component,
            "stability": s.business_stability_component,
        },
        "scored_at": s.scored_at.isoformat() if s.scored_at else None,
    } for s in scores]

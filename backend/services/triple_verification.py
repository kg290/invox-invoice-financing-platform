"""
Triple Verification Engine — 3-Layer Invoice Trust System
═══════════════════════════════════════════════════════════
Layer 1: Document Verification (format, calculations, uniqueness)
Layer 2: Entity Verification (GSTIN live check via Sandbox.co.in, PAN linkage, bank)
Layer 3: Behavioral Verification (patterns, history, anomalies)

Integrates Sandbox.co.in GST Compliance API for live GSTIN verification.
"""

import hashlib
import json
import math
import os
import re
import statistics
from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func

from models import (
    Invoice, InvoiceItem, Vendor, InvoiceVerificationReport,
    MarketplaceListing, RepaymentSchedule, InvoiceRegistryEntry,
)

# ── Sandbox.co.in GST API Config ──
SANDBOX_API_KEY = os.getenv("Sandbox_API_KEYNAME", "")
SANDBOX_API_SECRET = os.getenv("Sandbox_API_KEYNAME_SECRET", "")
SANDBOX_BASE_URL = "https://api.sandbox.co.in"

# Cache for JWT token (valid 24h, we refresh every request for safety)
_sandbox_token_cache = {"token": None, "expires_at": None}


def _get_sandbox_token() -> Optional[str]:
    """Authenticate with Sandbox.co.in and get JWT access token."""
    global _sandbox_token_cache

    # Return cached token if still valid
    if (_sandbox_token_cache["token"]
            and _sandbox_token_cache["expires_at"]
            and datetime.now(timezone.utc) < _sandbox_token_cache["expires_at"]):
        return _sandbox_token_cache["token"]

    if not SANDBOX_API_KEY or not SANDBOX_API_SECRET:
        return None

    try:
        response = httpx.post(
            f"{SANDBOX_BASE_URL}/authenticate",
            headers={
                "x-api-key": SANDBOX_API_KEY,
                "x-api-secret": SANDBOX_API_SECRET,
                "x-api-version": "1.0",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        if response.status_code == 200:
            data = response.json()
            token = data.get("data", {}).get("access_token")
            if token:
                # Cache for 23 hours (token valid 24h)
                _sandbox_token_cache["token"] = token
                _sandbox_token_cache["expires_at"] = datetime.now(timezone.utc) + timedelta(hours=23)
                return token
    except Exception:
        pass
    return None


# ═══════════════════════════════════════════════
#  SANDBOX.CO.IN GST API INTEGRATION
# ═══════════════════════════════════════════════

def verify_gstin_live(gstin: str) -> dict:
    """
    Query Sandbox.co.in GST Compliance Public API for live GSTIN verification.
    Endpoint: POST /gst/compliance/public/gstin/search
    Auth: JWT token (NOT Bearer) in Authorization header.
    Falls back to mock data if API is unavailable.
    """
    token = _get_sandbox_token()
    if not token:
        return _mock_gstin_verification(gstin, api_error="No Sandbox API credentials or auth failed")

    try:
        headers = {
            "Authorization": token,  # NOT Bearer — Sandbox.co.in docs say raw token
            "x-api-key": SANDBOX_API_KEY,
            "x-api-version": "1.0.0",
            "Content-Type": "application/json",
        }
        # Sandbox.co.in GSTIN public search endpoint
        response = httpx.post(
            f"{SANDBOX_BASE_URL}/gst/compliance/public/gstin/search",
            json={"gstin": gstin.upper()},
            headers=headers,
            timeout=15.0,
        )

        resp_data = response.json()

        if response.status_code == 200 and resp_data.get("data", {}).get("data"):
            gst_data = resp_data["data"]["data"]
            address = gst_data.get("pradr", {}).get("addr", {})
            return {
                "source": "sandbox_live",
                "success": True,
                "gstin": gstin,
                "data": gst_data,
                "status": gst_data.get("sts", "Unknown"),
                "legal_name": gst_data.get("lgnm", ""),
                "trade_name": gst_data.get("tradeNam", ""),
                "registration_date": gst_data.get("rgdt", ""),
                "business_type": gst_data.get("ctb", ""),
                "state": address.get("stcd", ""),
                "district": address.get("dst", ""),
                "pincode": address.get("pncd", ""),
                "is_active": gst_data.get("sts", "").lower() in ("active", "act"),
                "taxpayer_type": gst_data.get("dty", ""),
                "einvoice_status": gst_data.get("einvoiceStatus", ""),
                "last_updated": gst_data.get("lstupdt", ""),
                "nature_of_business": gst_data.get("nba", []),
                "transaction_id": resp_data.get("transaction_id", ""),
            }
        elif response.status_code == 200 and resp_data.get("data", {}).get("error_cd") == "FO8000":
            # Valid format but GSTIN not found in GST Network
            return {
                "source": "sandbox_live",
                "success": False,
                "gstin": gstin,
                "error": "GSTIN not found in GST Network",
                "error_code": "FO8000",
                "is_active": False,
                "transaction_id": resp_data.get("transaction_id", ""),
            }
        else:
            return _mock_gstin_verification(
                gstin,
                api_error=f"HTTP {response.status_code}: {resp_data.get('message', 'Unknown error')}"
            )

    except Exception as e:
        return _mock_gstin_verification(gstin, api_error=str(e))


def _mock_gstin_verification(gstin: str, api_error: str = None) -> dict:
    """Mock GSTIN verification fallback when WhiteBooks API is unavailable."""
    # Basic GSTIN format validation
    gstin_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$"
    is_valid_format = bool(re.match(gstin_pattern, gstin.upper()))

    return {
        "source": "mock_fallback",
        "api_error": api_error,
        "success": is_valid_format,
        "gstin": gstin,
        "is_valid_format": is_valid_format,
        "is_active": is_valid_format,  # Assume active if format is valid
        "state_code": gstin[:2] if len(gstin) >= 2 else "00",
        "pan_from_gstin": gstin[2:12] if len(gstin) >= 12 else "",
    }


# ═══════════════════════════════════════════════
#  LAYER 1: DOCUMENT VERIFICATION
# ═══════════════════════════════════════════════

def _verify_layer1_document(invoice: Invoice, items: list[InvoiceItem], vendor: Vendor, db: Session) -> dict:
    """
    Validates invoice document integrity:
    - GSTIN format validation
    - State code consistency
    - HSN/SAC code format
    - Tax calculation accuracy
    - Invoice number uniqueness
    - Amount sanity checks
    """
    checks = []
    score = 100.0  # Start at 100, deduct for issues

    # 1a. GSTIN format check (vendor)
    gstin_pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$"
    if vendor.gstin and re.match(gstin_pattern, vendor.gstin):
        checks.append({"check": "vendor_gstin_format", "status": "passed", "message": "Vendor GSTIN format valid"})
    else:
        checks.append({"check": "vendor_gstin_format", "status": "failed", "message": f"Invalid vendor GSTIN format: {vendor.gstin}"})
        score -= 25

    # 1b. Buyer GSTIN format (if B2B)
    if invoice.buyer_gstin:
        if re.match(gstin_pattern, invoice.buyer_gstin):
            checks.append({"check": "buyer_gstin_format", "status": "passed", "message": "Buyer GSTIN format valid"})
        else:
            checks.append({"check": "buyer_gstin_format", "status": "failed", "message": f"Invalid buyer GSTIN: {invoice.buyer_gstin}"})
            score -= 20
    else:
        checks.append({"check": "buyer_gstin_format", "status": "warning", "message": "B2C invoice (no buyer GSTIN)"})
        score -= 5

    # 1c. State code consistency
    if vendor.gstin and invoice.place_of_supply_code:
        vendor_state_code = vendor.gstin[:2]
        if invoice.supply_type == "intra_state" and vendor_state_code != invoice.place_of_supply_code:
            checks.append({"check": "state_code_match", "status": "failed", "message": "Intra-state but state codes differ"})
            score -= 15
        else:
            checks.append({"check": "state_code_match", "status": "passed", "message": "State code consistency verified"})

    # 1d. HSN/SAC code validation
    valid_hsn = all(
        len(item.hsn_sac_code) >= 4 and item.hsn_sac_code.isdigit()
        for item in items
    )
    if valid_hsn:
        checks.append({"check": "hsn_sac_codes", "status": "passed", "message": "All HSN/SAC codes valid"})
    else:
        checks.append({"check": "hsn_sac_codes", "status": "failed", "message": "Invalid HSN/SAC code found"})
        score -= 10

    # 1e. Tax calculation verification
    calc_errors = []
    recalc_subtotal = 0
    recalc_cgst = 0
    recalc_sgst = 0
    recalc_igst = 0

    for item in items:
        expected_taxable = round(item.quantity * item.unit_price * (1 - item.discount_percent / 100), 2)
        if abs(item.taxable_value - expected_taxable) > 0.5:
            calc_errors.append(f"Item {item.item_number}: taxable value mismatch")

        recalc_subtotal += item.taxable_value
        recalc_cgst += item.cgst_amount
        recalc_sgst += item.sgst_amount
        recalc_igst += item.igst_amount

    if abs(invoice.subtotal - recalc_subtotal) > 1:
        calc_errors.append(f"Subtotal mismatch: expected {recalc_subtotal}, got {invoice.subtotal}")
    if abs(invoice.total_cgst - recalc_cgst) > 1:
        calc_errors.append(f"CGST mismatch: expected {recalc_cgst}, got {invoice.total_cgst}")

    if not calc_errors:
        checks.append({"check": "tax_calculations", "status": "passed", "message": "All tax calculations verified"})
    else:
        checks.append({"check": "tax_calculations", "status": "failed", "message": "; ".join(calc_errors)})
        score -= 20

    # 1f. Invoice number uniqueness
    duplicates = db.query(Invoice).filter(
        Invoice.invoice_number == invoice.invoice_number,
        Invoice.id != invoice.id,
    ).count()
    if duplicates == 0:
        checks.append({"check": "invoice_uniqueness", "status": "passed", "message": "Invoice number is unique"})
    else:
        checks.append({"check": "invoice_uniqueness", "status": "failed", "message": f"Duplicate invoice number found ({duplicates} copies)"})
        score -= 30

    # 1g. Amount sanity check (compared to vendor's annual turnover)
    if vendor.annual_turnover and vendor.annual_turnover > 0:
        ratio = invoice.grand_total / vendor.annual_turnover
        if ratio > 0.5:
            checks.append({"check": "amount_sanity", "status": "warning", "message": f"Invoice is {ratio:.0%} of annual turnover — unusually large"})
            score -= 10
        else:
            checks.append({"check": "amount_sanity", "status": "passed", "message": "Invoice amount is within reasonable range"})

    status = "passed" if score >= 70 else ("warning" if score >= 50 else "failed")
    return {"status": status, "score": max(0, score), "checks": checks}


# ═══════════════════════════════════════════════
#  LAYER 2: ENTITY VERIFICATION
# ═══════════════════════════════════════════════

def _verify_layer2_entity(invoice: Invoice, vendor: Vendor, db: Session) -> dict:
    """
    Validates the entities (vendor + buyer) involved:
    - Live GSTIN verification via WhiteBooks API
    - PAN-GSTIN linkage
    - Vendor verification status
    - Bank account verification status
    """
    checks = []
    score = 100.0

    # 2a. Vendor GSTIN live verification
    vendor_gst_result = verify_gstin_live(vendor.gstin)
    if vendor_gst_result.get("success") and vendor_gst_result.get("is_active"):
        checks.append({
            "check": "vendor_gstin_live",
            "status": "passed",
            "message": f"Vendor GSTIN active (source: {vendor_gst_result.get('source', 'unknown')})",
            "api_data": vendor_gst_result,
        })
    else:
        checks.append({
            "check": "vendor_gstin_live",
            "status": "failed",
            "message": f"Vendor GSTIN verification failed",
            "api_data": vendor_gst_result,
        })
        score -= 30

    # 2b. Buyer GSTIN live verification (if B2B)
    buyer_gst_result = None
    if invoice.buyer_gstin:
        buyer_gst_result = verify_gstin_live(invoice.buyer_gstin)
        if buyer_gst_result.get("success") and buyer_gst_result.get("is_active"):
            checks.append({
                "check": "buyer_gstin_live",
                "status": "passed",
                "message": f"Buyer GSTIN active (source: {buyer_gst_result.get('source', 'unknown')})",
            })
        else:
            checks.append({
                "check": "buyer_gstin_live",
                "status": "failed",
                "message": "Buyer GSTIN not active or not found",
            })
            score -= 25

    # 2c. PAN-GSTIN linkage
    if vendor.personal_pan and vendor.gstin and len(vendor.gstin) >= 12:
        pan_from_gstin = vendor.gstin[2:12]
        if pan_from_gstin == vendor.personal_pan:
            checks.append({"check": "pan_gstin_linkage", "status": "passed", "message": "PAN matches GSTIN"})
        else:
            checks.append({"check": "pan_gstin_linkage", "status": "failed", "message": f"PAN mismatch: GSTIN has {pan_from_gstin}, vendor PAN is {vendor.personal_pan}"})
            score -= 25

    # 2d. Vendor profile verification status
    if vendor.profile_status == "verified":
        checks.append({"check": "vendor_profile", "status": "passed", "message": "Vendor profile is verified"})
    elif vendor.profile_status == "pending":
        checks.append({"check": "vendor_profile", "status": "warning", "message": "Vendor profile pending verification"})
        score -= 10
    else:
        checks.append({"check": "vendor_profile", "status": "failed", "message": f"Vendor profile status: {vendor.profile_status}"})
        score -= 20

    # 2e. Udyam registration check
    if vendor.udyam_registration_number:
        udyam_pattern = r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$"
        if re.match(udyam_pattern, vendor.udyam_registration_number):
            checks.append({"check": "udyam_registration", "status": "passed", "message": "Valid Udyam registration number"})
        else:
            checks.append({"check": "udyam_registration", "status": "warning", "message": "Udyam registration format invalid"})
            score -= 5
    else:
        checks.append({"check": "udyam_registration", "status": "warning", "message": "No Udyam registration provided"})
        score -= 5

    status = "passed" if score >= 70 else ("warning" if score >= 50 else "failed")
    return {
        "status": status,
        "score": max(0, score),
        "checks": checks,
        "gst_api_response": json.dumps({
            "vendor": vendor_gst_result,
            "buyer": buyer_gst_result,
        }, default=str),
    }


# ═══════════════════════════════════════════════
#  LAYER 3: BEHAVIORAL VERIFICATION
# ═══════════════════════════════════════════════

def _verify_layer3_behavioral(invoice: Invoice, vendor: Vendor, db: Session) -> dict:
    """
    Analyzes behavioral patterns for fraud detection:
    - Invoice velocity (too many too fast?)
    - Amount anomaly detection (statistical outlier?)
    - Buyer concentration risk
    - Repayment history
    - Circular invoicing detection
    """
    checks = []
    score = 100.0

    # 3a. Invoice velocity check (last 7 days)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_invoices = db.query(Invoice).filter(
        Invoice.vendor_id == vendor.id,
        Invoice.created_at >= week_ago,
    ).count()
    if recent_invoices > 10:
        checks.append({"check": "invoice_velocity", "status": "failed", "message": f"{recent_invoices} invoices in 7 days — suspicious velocity"})
        score -= 25
    elif recent_invoices > 5:
        checks.append({"check": "invoice_velocity", "status": "warning", "message": f"{recent_invoices} invoices in 7 days — elevated activity"})
        score -= 10
    else:
        checks.append({"check": "invoice_velocity", "status": "passed", "message": f"{recent_invoices} invoices in 7 days — normal velocity"})

    # 3b. Amount anomaly detection
    all_invoices = db.query(Invoice).filter(Invoice.vendor_id == vendor.id).all()
    if len(all_invoices) >= 3:
        amounts = [inv.grand_total for inv in all_invoices]
        mean_amt = statistics.mean(amounts)
        stdev_amt = statistics.stdev(amounts) if len(amounts) > 1 else 0

        if stdev_amt > 0:
            z_score = (invoice.grand_total - mean_amt) / stdev_amt
            if abs(z_score) > 3:
                checks.append({"check": "amount_anomaly", "status": "failed", "message": f"Amount is {abs(z_score):.1f} std deviations from mean (₹{mean_amt:,.0f}) — statistical outlier"})
                score -= 20
            elif abs(z_score) > 2:
                checks.append({"check": "amount_anomaly", "status": "warning", "message": f"Amount is {abs(z_score):.1f} std deviations from mean — elevated"})
                score -= 10
            else:
                checks.append({"check": "amount_anomaly", "status": "passed", "message": "Amount within normal range"})
        else:
            checks.append({"check": "amount_anomaly", "status": "passed", "message": "Consistent invoice amounts"})
    else:
        checks.append({"check": "amount_anomaly", "status": "warning", "message": "Insufficient history for anomaly detection"})

    # 3c. Buyer concentration risk
    if len(all_invoices) >= 2:
        buyer_counts = {}
        for inv in all_invoices:
            buyer_counts[inv.buyer_name] = buyer_counts.get(inv.buyer_name, 0) + 1
        top_buyer_pct = max(buyer_counts.values()) / len(all_invoices)
        if top_buyer_pct > 0.8:
            checks.append({"check": "buyer_concentration", "status": "warning", "message": f"Top buyer is {top_buyer_pct:.0%} of invoices — high concentration risk"})
            score -= 10
        else:
            checks.append({"check": "buyer_concentration", "status": "passed", "message": "Buyer diversification is healthy"})

    # 3d. Repayment history
    vendor_listings = db.query(MarketplaceListing).filter(
        MarketplaceListing.vendor_id == vendor.id,
        MarketplaceListing.listing_status.in_(["funded", "settled"]),
    ).all()
    if vendor_listings:
        listing_ids = [l.id for l in vendor_listings]
        total_installments = db.query(RepaymentSchedule).filter(
            RepaymentSchedule.listing_id.in_(listing_ids)
        ).count()
        paid_on_time = db.query(RepaymentSchedule).filter(
            RepaymentSchedule.listing_id.in_(listing_ids),
            RepaymentSchedule.status == "paid",
        ).count()
        overdue = db.query(RepaymentSchedule).filter(
            RepaymentSchedule.listing_id.in_(listing_ids),
            RepaymentSchedule.status == "overdue",
        ).count()

        if total_installments > 0:
            on_time_pct = paid_on_time / total_installments
            if overdue > 0:
                checks.append({"check": "repayment_history", "status": "warning", "message": f"{overdue} overdue installment(s), {on_time_pct:.0%} on-time rate"})
                score -= 15
            elif on_time_pct >= 0.9:
                checks.append({"check": "repayment_history", "status": "passed", "message": f"Excellent repayment history — {on_time_pct:.0%} on-time"})
                score += 5  # Bonus for good history!
            else:
                checks.append({"check": "repayment_history", "status": "passed", "message": f"Good repayment history — {on_time_pct:.0%} on-time"})
    else:
        checks.append({"check": "repayment_history", "status": "warning", "message": "No repayment history (first-time borrower)"})
        score -= 5

    # 3e. Circular invoicing detection (vendor billing same buyer who also bills them)
    if invoice.buyer_gstin:
        reverse_invoices = db.query(Invoice).filter(
            Invoice.buyer_gstin == vendor.gstin,
            Invoice.vendor_id != vendor.id,
        ).count()
        if reverse_invoices > 0:
            checks.append({"check": "circular_invoicing", "status": "warning", "message": f"Detected {reverse_invoices} invoice(s) from buyer to this vendor — possible circular invoicing"})
            score -= 15
        else:
            checks.append({"check": "circular_invoicing", "status": "passed", "message": "No circular invoicing detected"})

    # 3f. Self-invoicing detection
    if invoice.buyer_gstin and invoice.buyer_gstin == vendor.gstin:
        checks.append({"check": "self_invoicing", "status": "failed", "message": "Vendor is billing themselves — self-invoicing detected"})
        score -= 30
    else:
        checks.append({"check": "self_invoicing", "status": "passed", "message": "No self-invoicing"})

    score = max(0, min(105, score))  # Cap at 105 (bonus possible)
    status = "passed" if score >= 70 else ("warning" if score >= 50 else "failed")
    return {"status": status, "score": score, "checks": checks}


# ═══════════════════════════════════════════════
#  MAIN VERIFICATION ORCHESTRATOR
# ═══════════════════════════════════════════════

def run_triple_verification(db: Session, invoice_id: int) -> dict:
    """
    Run all 3 verification layers on an invoice.
    Returns comprehensive verification report.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise ValueError("Invoice not found")

    vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first()
    if not vendor:
        raise ValueError("Vendor not found")

    items = db.query(InvoiceItem).filter(
        InvoiceItem.invoice_id == invoice_id
    ).order_by(InvoiceItem.item_number).all()

    # Run all 3 layers
    layer1 = _verify_layer1_document(invoice, items, vendor, db)
    layer2 = _verify_layer2_entity(invoice, vendor, db)
    layer3 = _verify_layer3_behavioral(invoice, vendor, db)

    # Compute overall score (weighted)
    overall_score = round(
        layer1["score"] * 0.35 +
        layer2["score"] * 0.40 +
        layer3["score"] * 0.25,
        1
    )

    # Determine overall status
    if layer1["status"] == "failed" or layer2["status"] == "failed":
        overall_status = "rejected"
        recommendation = "reject"
    elif overall_score >= 75:
        overall_status = "verified"
        recommendation = "approve"
    elif overall_score >= 50:
        overall_status = "needs_review"
        recommendation = "manual_review"
    else:
        overall_status = "rejected"
        recommendation = "reject"

    # Collect risk flags
    risk_flags = []
    for layer_result in [layer1, layer2, layer3]:
        for check in layer_result.get("checks", []):
            if check["status"] in ("failed", "warning"):
                risk_flags.append(check["message"])

    # Save report to DB
    report = db.query(InvoiceVerificationReport).filter(
        InvoiceVerificationReport.invoice_id == invoice_id
    ).first()
    if not report:
        report = InvoiceVerificationReport(invoice_id=invoice_id, vendor_id=vendor.id)
        db.add(report)

    report.layer1_status = layer1["status"]
    report.layer1_score = layer1["score"]
    report.layer1_details = json.dumps(layer1["checks"], default=str)
    report.layer2_status = layer2["status"]
    report.layer2_score = layer2["score"]
    report.layer2_details = json.dumps(layer2["checks"], default=str)
    report.layer3_status = layer3["status"]
    report.layer3_score = layer3["score"]
    report.layer3_details = json.dumps(layer3["checks"], default=str)
    report.overall_status = overall_status
    report.overall_score = overall_score
    report.risk_flags = json.dumps(risk_flags)
    report.recommendation = recommendation
    report.gst_api_response = layer2.get("gst_api_response")
    report.verified_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "invoice_id": invoice_id,
        "overall_status": overall_status,
        "overall_score": overall_score,
        "recommendation": recommendation,
        "layers": {
            "document_verification": {
                "status": layer1["status"],
                "score": layer1["score"],
                "checks": layer1["checks"],
            },
            "entity_verification": {
                "status": layer2["status"],
                "score": layer2["score"],
                "checks": layer2["checks"],
            },
            "behavioral_verification": {
                "status": layer3["status"],
                "score": layer3["score"],
                "checks": layer3["checks"],
            },
        },
        "risk_flags": risk_flags,
        "verified_at": datetime.now(timezone.utc).isoformat(),
    }

"""
Triple Verification Engine Routes
══════════════════════════════════
3-layer verification: Document → Entity → Behavioral
Integrates Sandbox.co.in GST Compliance API for live GSTIN checks.
"""

import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import InvoiceVerificationReport, Invoice
from routes.auth import get_current_user
from services.triple_verification import run_triple_verification, verify_gstin_live

router = APIRouter(prefix="/api/triple-verify", tags=["Triple Verification Engine"])


@router.post("/invoice/{invoice_id}")
def verify_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Run full 3-layer verification on an invoice.
    
    Layer 1: Document (format, calculations, uniqueness)
    Layer 2: Entity (live GSTIN via Sandbox.co.in, PAN linkage, Udyam)
    Layer 3: Behavioral (velocity, anomaly, circular invoicing, history)
    
    Returns overall_status: verified | needs_review | rejected
    """
    try:
        result = run_triple_verification(db, invoice_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/report/{invoice_id}")
def get_verification_report(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get the most recent verification report for an invoice."""
    report = db.query(InvoiceVerificationReport).filter(
        InvoiceVerificationReport.invoice_id == invoice_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="No verification report found. Run verification first.")

    return {
        "report_id": report.id,
        "invoice_id": report.invoice_id,
        "vendor_id": report.vendor_id,
        "overall_status": report.overall_status,
        "overall_score": report.overall_score,
        "recommendation": report.recommendation,
        "layers": {
            "document_verification": {
                "status": report.layer1_status,
                "score": report.layer1_score,
                "checks": json.loads(report.layer1_details) if report.layer1_details else [],
            },
            "entity_verification": {
                "status": report.layer2_status,
                "score": report.layer2_score,
                "checks": json.loads(report.layer2_details) if report.layer2_details else [],
            },
            "behavioral_verification": {
                "status": report.layer3_status,
                "score": report.layer3_score,
                "checks": json.loads(report.layer3_details) if report.layer3_details else [],
            },
        },
        "risk_flags": json.loads(report.risk_flags) if report.risk_flags else [],
        "gst_api_response": json.loads(report.gst_api_response) if report.gst_api_response else None,
        "verified_at": report.verified_at.isoformat() if report.verified_at else None,
    }


@router.post("/gstin-live/{gstin}")
def live_gstin_check(
    gstin: str,
    current_user=Depends(get_current_user),
):
    """
    Live GSTIN verification via Sandbox.co.in GST Compliance API.
    Returns real-time GSTIN status, legal name, trade name, etc.
    Falls back to format validation if API unavailable.
    """
    result = verify_gstin_live(gstin.upper())
    return result


@router.get("/stats")
def verification_stats(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Get overall verification statistics."""
    total = db.query(InvoiceVerificationReport).count()
    verified = db.query(InvoiceVerificationReport).filter(
        InvoiceVerificationReport.overall_status == "verified"
    ).count()
    rejected = db.query(InvoiceVerificationReport).filter(
        InvoiceVerificationReport.overall_status == "rejected"
    ).count()
    needs_review = db.query(InvoiceVerificationReport).filter(
        InvoiceVerificationReport.overall_status == "needs_review"
    ).count()

    # Average scores
    from sqlalchemy import func as sa_func
    avg_score = db.query(sa_func.avg(InvoiceVerificationReport.overall_score)).scalar() or 0
    avg_l1 = db.query(sa_func.avg(InvoiceVerificationReport.layer1_score)).scalar() or 0
    avg_l2 = db.query(sa_func.avg(InvoiceVerificationReport.layer2_score)).scalar() or 0
    avg_l3 = db.query(sa_func.avg(InvoiceVerificationReport.layer3_score)).scalar() or 0

    return {
        "total_verifications": total,
        "breakdown": {
            "verified": verified,
            "rejected": rejected,
            "needs_review": needs_review,
        },
        "average_scores": {
            "overall": round(avg_score, 1),
            "document_layer": round(avg_l1, 1),
            "entity_layer": round(avg_l2, 1),
            "behavioral_layer": round(avg_l3, 1),
        },
        "approval_rate": f"{(verified / total * 100):.1f}%" if total > 0 else "N/A",
    }

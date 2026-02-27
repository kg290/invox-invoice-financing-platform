"""Credit Scoring Engine — API Routes"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Vendor, CreditScore
from services.credit_scoring import compute_credit_score, get_credit_score_history

router = APIRouter(prefix="/api/credit-score", tags=["Credit Scoring"])


@router.get("/vendor/{vendor_id}")
def get_or_compute_score(vendor_id: int, force_refresh: bool = False, db: Session = Depends(get_db)):
    """Get cached score or compute fresh score."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(404, "Vendor not found")

    if not force_refresh:
        from datetime import datetime, timezone
        latest = db.query(CreditScore).filter(
            CreditScore.vendor_id == vendor_id
        ).order_by(CreditScore.scored_at.desc()).first()
        if latest and latest.expires_at:
            expires = latest.expires_at
            now = datetime.now(timezone.utc)
            # Make both aware or both naive for comparison
            if expires.tzinfo is None:
                from datetime import timezone as tz
                expires = expires.replace(tzinfo=tz.utc)
            if expires > now:
                import json
                return {
                    "score_id": latest.id,
                    "vendor_id": vendor_id,
                    "total_score": latest.total_score,
                    "risk_grade": latest.risk_grade,
                    "confidence_level": latest.confidence_level,
                    "recommendations": {
                        "interest_rate": latest.recommended_interest_rate,
                        "max_funding_amount": latest.recommended_max_funding,
                        "max_tenure_days": latest.recommended_max_tenure_days,
                    },
                    "cached": True,
                    "scored_at": latest.scored_at.isoformat() if latest.scored_at else None,
                    "valid_until": latest.expires_at.isoformat() if latest.expires_at else None,
                }

    try:
        result = compute_credit_score(db, vendor_id)
        result["cached"] = False
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/breakdown/{vendor_id}")
def get_score_breakdown(vendor_id: int, db: Session = Depends(get_db)):
    """Compute and return full breakdown."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    try:
        return compute_credit_score(db, vendor_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/history/{vendor_id}")
def get_score_history(vendor_id: int, db: Session = Depends(get_db)):
    """Get credit score trend over time."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(404, "Vendor not found")
    history = get_credit_score_history(db, vendor_id)
    return {"vendor_id": vendor_id, "history": history, "count": len(history)}


@router.get("/recommended-rate/{vendor_id}")
def get_recommended_rate(vendor_id: int, invoice_amount: float = 100000, db: Session = Depends(get_db)):
    """Get recommended financing rate for a vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(404, "Vendor not found")

    result = compute_credit_score(db, vendor_id)
    rec = result["recommendations"]
    return {
        "vendor_id": vendor_id,
        "risk_grade": result["risk_grade"],
        "total_score": result["total_score"],
        "recommended_rate": rec["interest_rate"],
        "max_funding_percentage": rec["max_funding_percentage"],
        "max_tenure_days": rec["max_tenure_days"],
        "invoice_amount": invoice_amount,
        "eligible_funding": round(invoice_amount * rec["max_funding_percentage"] / 100, 2),
    }

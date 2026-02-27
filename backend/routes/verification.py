from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Vendor, VerificationCheck, User
from verification import run_full_verification
from routes.auth import get_current_user
import json

router = APIRouter(prefix="/api/verification", tags=["verification"])


@router.post("/{vendor_id}/verify")
def verify_vendor(vendor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Run full verification pipeline on a vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    results = run_full_verification(db, vendor)
    return results


@router.get("/{vendor_id}/status")
def get_verification_status(vendor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all verification checks for a vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    checks = db.query(VerificationCheck).filter(
        VerificationCheck.vendor_id == vendor_id
    ).order_by(VerificationCheck.checked_at.desc()).all()

    return {
        "vendor_id": vendor_id,
        "profile_status": vendor.profile_status,
        "checks": [
            {
                "id": c.id,
                "check_type": c.check_type,
                "status": c.status,
                "details": json.loads(c.details) if c.details else {},
                "checked_at": c.checked_at.isoformat() if c.checked_at else None,
            }
            for c in checks
        ],
    }

"""e-Mandate Auto-Repayment — API Routes"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from services.emandate import (
    register_mandate, get_mandate, pause_mandate,
    resume_mandate, revoke_mandate, execute_auto_debit,
    retry_failed_debits, get_vendor_mandates,
)

router = APIRouter(prefix="/api/emandate", tags=["e-Mandate Auto-Repayment"])


class RegisterMandateRequest(BaseModel):
    vendor_id: int
    max_amount: float
    frequency: str = "monthly"
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class ExecuteDebitRequest(BaseModel):
    mandate_id: int
    installment_id: int


@router.post("/register")
def register(req: RegisterMandateRequest, db: Session = Depends(get_db)):
    """Register a new e-Mandate for auto-repayment."""
    try:
        return register_mandate(
            db, req.vendor_id, req.max_amount, req.frequency,
            req.start_date, req.end_date,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/mandate/{mandate_id}")
def get_mandate_details(mandate_id: int, db: Session = Depends(get_db)):
    """Get mandate details and recent executions."""
    try:
        return get_mandate(db, mandate_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/mandate/{mandate_id}/pause")
def pause(mandate_id: int, db: Session = Depends(get_db)):
    """Pause an active mandate."""
    try:
        return pause_mandate(db, mandate_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/mandate/{mandate_id}/resume")
def resume(mandate_id: int, db: Session = Depends(get_db)):
    """Resume a paused mandate."""
    try:
        return resume_mandate(db, mandate_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/mandate/{mandate_id}/revoke")
def revoke(mandate_id: int, db: Session = Depends(get_db)):
    """Permanently revoke a mandate."""
    try:
        return revoke_mandate(db, mandate_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/execute")
def execute(req: ExecuteDebitRequest, db: Session = Depends(get_db)):
    """Execute an auto-debit against a mandate for a specific installment."""
    try:
        return execute_auto_debit(db, req.mandate_id, req.installment_id)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/retry-failed")
def retry_all_failed(db: Session = Depends(get_db)):
    """Batch retry all failed auto-debits (cron endpoint)."""
    return retry_failed_debits(db)


@router.get("/vendor/{vendor_id}")
def vendor_mandates(vendor_id: int, db: Session = Depends(get_db)):
    """List all mandates for a vendor."""
    mandates = get_vendor_mandates(db, vendor_id)
    return {"vendor_id": vendor_id, "total": len(mandates), "mandates": mandates}

"""Invoice Factoring — API Routes"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from models import FactoringAgreement
from services.factoring import (
    get_factoring_options,
    create_factoring_agreement,
    get_factoring_agreement,
)

router = APIRouter(prefix="/api/factoring", tags=["Invoice Factoring"])


class CreateFactoringRequest(BaseModel):
    listing_id: int
    lender_id: int
    factoring_type: str  # non_recourse | partial_recourse | full_recourse
    mandate_id: Optional[int] = None


@router.get("/options/{listing_id}")
def get_options(listing_id: int, db: Session = Depends(get_db)):
    """Get available factoring options with dynamic pricing for a listing."""
    try:
        return get_factoring_options(db, listing_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/create")
def create_agreement(req: CreateFactoringRequest, db: Session = Depends(get_db)):
    """Create a factoring agreement with selected recourse type."""
    try:
        return create_factoring_agreement(
            db, req.listing_id, req.lender_id, req.factoring_type, req.mandate_id
        )
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/agreement/{agreement_id}")
def get_agreement(agreement_id: int, db: Session = Depends(get_db)):
    """Get factoring agreement details."""
    try:
        return get_factoring_agreement(db, agreement_id)
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/vendor/{vendor_id}")
def list_vendor_agreements(vendor_id: int, db: Session = Depends(get_db)):
    """List all factoring agreements for a vendor."""
    agreements = db.query(FactoringAgreement).filter(
        FactoringAgreement.vendor_id == vendor_id
    ).order_by(FactoringAgreement.created_at.desc()).all()

    return {
        "vendor_id": vendor_id,
        "total": len(agreements),
        "agreements": [{
            "agreement_id": a.id,
            "listing_id": a.listing_id,
            "factoring_type": a.factoring_type,
            "recourse_percentage": a.recourse_percentage,
            "effective_rate": a.effective_interest_rate,
            "invoice_amount": a.invoice_amount,
            "funded_amount": a.funded_amount,
            "status": a.agreement_status,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in agreements],
    }


@router.get("/lender/{lender_id}")
def list_lender_agreements(lender_id: int, db: Session = Depends(get_db)):
    """List all factoring agreements funded by a lender."""
    agreements = db.query(FactoringAgreement).filter(
        FactoringAgreement.lender_id == lender_id
    ).order_by(FactoringAgreement.created_at.desc()).all()

    return {
        "lender_id": lender_id,
        "total": len(agreements),
        "agreements": [{
            "agreement_id": a.id,
            "listing_id": a.listing_id,
            "factoring_type": a.factoring_type,
            "recourse_percentage": a.recourse_percentage,
            "effective_rate": a.effective_interest_rate,
            "invoice_amount": a.invoice_amount,
            "funded_amount": a.funded_amount,
            "status": a.agreement_status,
            "vendor_credit_score": a.vendor_credit_score,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        } for a in agreements],
    }

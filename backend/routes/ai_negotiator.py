"""
AI Negotiator — Chat-Based API Routes
══════════════════════════════════════
Endpoints:
  POST /api/negotiate/{listing_id}/start     — Lender opens a chat
  POST /api/negotiate/{session_id}/offer     — Lender sends an offer
  GET  /api/negotiate/chat/{session_id}      — Get chat messages
  GET  /api/negotiate/listing/{listing_id}   — All negotiations on a listing
  GET  /api/negotiate/vendor/{vendor_id}     — Vendor's negotiations
  GET  /api/negotiate/my                     — Current user's negotiations
"""

from pydantic import BaseModel, Field
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services.ai_negotiator import (
    start_chat, process_offer, get_chat,
    get_listing_negotiations, get_vendor_negotiations, get_lender_negotiations,
    lock_price_accept,
)
from routes.auth import get_current_user

router = APIRouter(prefix="/api/negotiate", tags=["AI Negotiator"])


class OfferPayload(BaseModel):
    rate: float = Field(..., gt=0, le=50, description="Offered interest rate (%)")
    amount: float = Field(..., gt=0, description="Offered funding amount (₹)")
    message: Optional[str] = Field("", description="Optional message from lender")


# ─── Lender starts a chat ───
@router.post("/{listing_id}/start")
def start_negotiation_chat(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lender opens a negotiation chat on a marketplace listing."""
    if current_user.role != "lender":
        raise HTTPException(status_code=403, detail="Only lenders can start negotiations")
    try:
        return start_chat(db, listing_id, current_user)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Lender sends an offer ───
@router.post("/{session_id}/offer")
def send_offer(
    session_id: int,
    payload: OfferPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lender sends a rate + amount offer. AI agent responds in the chat."""
    if current_user.role != "lender":
        raise HTTPException(status_code=403, detail="Only lenders can send offers")
    try:
        return process_offer(
            db, session_id, current_user,
            payload.rate, payload.amount, payload.message or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Lock price — accept listed price without negotiation ───
class LockPricePayload(BaseModel):
    amount: float = Field(..., gt=0, description="Investment amount (₹)")


@router.post("/{listing_id}/lock-price")
def lock_price(
    listing_id: int,
    payload: LockPricePayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lender accepts the listed price and skips negotiation entirely."""
    if current_user.role != "lender":
        raise HTTPException(status_code=403, detail="Only lenders can lock price")
    try:
        return lock_price_accept(db, listing_id, current_user, payload.amount)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ─── Get a specific chat ───
@router.get("/chat/{session_id}")
def get_negotiation_chat(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the full chat history for a negotiation session."""
    result = get_chat(db, session_id)
    if not result:
        raise HTTPException(status_code=404, detail="Chat not found")
    return result


# ─── All negotiations on a listing (for vendor or any viewer) ───
@router.get("/listing/{listing_id}")
def listing_negotiations(
    listing_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all negotiation chats for a marketplace listing."""
    return get_listing_negotiations(db, listing_id)


# ─── Vendor's negotiations ───
@router.get("/vendor/{vendor_id}")
def vendor_negotiations(
    vendor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all negotiations across a vendor's listings."""
    return get_vendor_negotiations(db, vendor_id)


# ─── Current user's negotiations ───
@router.get("/my")
def my_negotiations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get negotiations for the current logged-in user (lender or vendor)."""
    if current_user.role == "lender":
        return get_lender_negotiations(db, current_user.id)
    elif current_user.role == "vendor" and current_user.vendor_id:
        return get_vendor_negotiations(db, current_user.vendor_id)
    return []

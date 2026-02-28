"""
Admin routes — platform overview, vendor management, default handling.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from database import get_db
from models import User, Vendor, Lender, Invoice, MarketplaceListing, RepaymentSchedule, VerificationCheck, ActivityLog, Notification, FractionalInvestment
from routes.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


class AdminActionRequest(BaseModel):
    action: str
    note: Optional[str] = None
    penalty_amount: Optional[float] = None


def _require_admin(user: User):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")


# ═══════════════════════════════════════════════
#  PLATFORM OVERVIEW
# ═══════════════════════════════════════════════

@router.get("/overview")
def admin_overview(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get platform-wide stats for admin dashboard."""
    _require_admin(current_user)

    total_vendors = db.query(Vendor).count()
    verified_vendors = db.query(Vendor).filter(Vendor.profile_status == "verified").count()
    total_lenders = db.query(Lender).count()
    total_users = db.query(User).count()

    total_invoices = db.query(Invoice).count()
    total_invoice_value = db.query(func.sum(Invoice.grand_total)).scalar() or 0
    paid_invoices = db.query(Invoice).filter(Invoice.payment_status == "paid").count()

    total_listings = db.query(MarketplaceListing).count()
    funded_listings = db.query(MarketplaceListing).filter(MarketplaceListing.listing_status == "funded").count()
    settled_listings = db.query(MarketplaceListing).filter(MarketplaceListing.listing_status == "settled").count()
    total_funded_amount = db.query(func.sum(MarketplaceListing.funded_amount)).filter(
        MarketplaceListing.listing_status.in_(["funded", "settled"])
    ).scalar() or 0

    # Repayment stats
    total_repayment_due = db.query(func.sum(RepaymentSchedule.total_amount)).scalar() or 0
    total_repayment_paid = db.query(func.sum(RepaymentSchedule.paid_amount)).filter(
        RepaymentSchedule.status == "paid"
    ).scalar() or 0
    overdue_installments = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.status == "pending",
        RepaymentSchedule.due_date < datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    ).count()

    return {
        "users": {
            "total": total_users,
            "vendors": total_vendors,
            "verified_vendors": verified_vendors,
            "lenders": total_lenders,
        },
        "invoices": {
            "total": total_invoices,
            "total_value": total_invoice_value,
            "paid": paid_invoices,
        },
        "marketplace": {
            "total_listings": total_listings,
            "funded": funded_listings,
            "settled": settled_listings,
            "total_funded_amount": total_funded_amount,
        },
        "repayments": {
            "total_due": total_repayment_due,
            "total_paid": total_repayment_paid,
            "overdue_installments": overdue_installments,
        },
    }


# ═══════════════════════════════════════════════
#  VENDORS LIST
# ═══════════════════════════════════════════════

@router.get("/vendors")
def admin_vendors(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all vendors with key details."""
    _require_admin(current_user)

    vendors = db.query(Vendor).all()
    result = []
    for v in vendors:
        # Get repayment stats for this vendor
        vendor_listings = db.query(MarketplaceListing).filter(
            MarketplaceListing.vendor_id == v.id,
            MarketplaceListing.listing_status.in_(["funded", "settled"]),
        ).all()
        listing_ids = [l.id for l in vendor_listings]

        overdue = 0
        total_owed = 0
        if listing_ids:
            overdue = db.query(RepaymentSchedule).filter(
                RepaymentSchedule.listing_id.in_(listing_ids),
                RepaymentSchedule.status == "pending",
                RepaymentSchedule.due_date < datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            ).count()
            total_owed_val = db.query(func.sum(RepaymentSchedule.total_amount)).filter(
                RepaymentSchedule.listing_id.in_(listing_ids),
                RepaymentSchedule.status == "pending",
            ).scalar()
            total_owed = total_owed_val or 0

        result.append({
            "id": v.id,
            "name": v.full_name,
            "business_name": v.business_name,
            "email": v.email,
            "phone": v.phone,
            "gstin": v.gstin,
            "profile_status": v.profile_status,
            "risk_score": v.risk_score,
            "cibil_score": v.cibil_score,
            "total_owed": total_owed,
            "overdue_installments": overdue,
            "blacklisted": getattr(v, 'blacklisted', False),
            "penalty_amount": getattr(v, 'penalty_amount', 0),
            "total_defaults": getattr(v, 'total_defaults', 0),
        })

    return result


# ═══════════════════════════════════════════════
#  LENDERS LIST
# ═══════════════════════════════════════════════

@router.get("/lenders")
def admin_lenders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all lenders."""
    _require_admin(current_user)

    lenders = db.query(Lender).all()
    return [{
        "id": l.id,
        "name": l.name,
        "email": l.email,
        "organization": l.organization,
        "lender_type": l.lender_type,
    } for l in lenders]


# ═══════════════════════════════════════════════
#  DEFAULTS / OVERDUE
# ═══════════════════════════════════════════════

@router.get("/defaults")
def admin_defaults(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all overdue repayment installments grouped by vendor."""
    _require_admin(current_user)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    overdue = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.status == "pending",
        RepaymentSchedule.due_date < today,
    ).all()

    # Group by listing → vendor
    defaults = {}
    for s in overdue:
        listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == s.listing_id).first()
        if not listing:
            continue
        vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()
        if not vendor:
            continue

        key = vendor.id
        if key not in defaults:
            defaults[key] = {
                "vendor_id": vendor.id,
                "vendor_name": vendor.full_name,
                "business_name": vendor.business_name,
                "phone": vendor.phone,
                "email": vendor.email,
                "risk_score": vendor.risk_score,
                "profile_status": vendor.profile_status,
                "blacklisted": getattr(vendor, 'blacklisted', False),
                "penalty_amount": getattr(vendor, 'penalty_amount', 0),
                "total_defaults": getattr(vendor, 'total_defaults', 0),
                "overdue_amount": 0,
                "overdue_installments": [],
            }

        defaults[key]["overdue_amount"] += s.total_amount
        defaults[key]["overdue_installments"].append({
            "id": s.id,
            "listing_id": s.listing_id,
            "installment_number": s.installment_number,
            "due_date": s.due_date,
            "total_amount": s.total_amount,
        })

    return list(defaults.values())


# ═══════════════════════════════════════════════
#  ADMIN ACTIONS  (enhanced for defaulter mgmt)
# ═══════════════════════════════════════════════

@router.post("/vendor/{vendor_id}/action")
def admin_vendor_action(
    vendor_id: int,
    body: AdminActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin action on a vendor — suspend, warn, approve, blacklist, penalty, send_notice, freeze, unfreeze, reinstate."""
    _require_admin(current_user)

    action = body.action
    note = body.note

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # ---------- action handlers ----------
    if action == "suspend":
        vendor.profile_status = "suspended"
        vendor.verification_notes = f"Suspended by admin. {note or ''}"

    elif action == "approve":
        vendor.profile_status = "verified"
        vendor.verification_notes = f"Approved by admin. {note or ''}"

    elif action == "warn":
        vendor.verification_notes = f"Admin Warning: {note or 'Payment overdue'}"
        # also send in-app notification
        notif = Notification(
            user_id=vendor.user_id,
            title="⚠️ Admin Warning",
            message=note or "You have overdue payments. Please clear them immediately.",
            type="warning",
        )
        db.add(notif)

    elif action == "blacklist":
        vendor.blacklisted = True
        vendor.blacklisted_at = datetime.utcnow()
        vendor.blacklist_reason = note or "Repeated payment defaults"
        vendor.profile_status = "blacklisted"
        vendor.total_defaults = (vendor.total_defaults or 0) + 1
        vendor.verification_notes = f"Blacklisted by admin. {note or ''}"
        notif = Notification(
            user_id=vendor.user_id,
            title="🚫 Account Blacklisted",
            message=f"Your account has been blacklisted. Reason: {note or 'Payment defaults'}. Contact support to appeal.",
            type="critical",
        )
        db.add(notif)

    elif action == "impose_penalty":
        amount = body.penalty_amount or 0
        if amount <= 0:
            raise HTTPException(status_code=400, detail="penalty_amount must be > 0")
        vendor.penalty_amount = (vendor.penalty_amount or 0) + amount
        vendor.penalty_reason = note or "Late payment penalty"
        vendor.verification_notes = f"Penalty ₹{amount:.2f} imposed. {note or ''}"
        notif = Notification(
            user_id=vendor.user_id,
            title="💰 Penalty Imposed",
            message=f"A penalty of ₹{amount:.2f} has been imposed on your account. Reason: {note or 'Late payment'}.",
            type="warning",
        )
        db.add(notif)

    elif action == "send_notice":
        notif = Notification(
            user_id=vendor.user_id,
            title="📋 Legal / Recovery Notice",
            message=note or "You are hereby notified of outstanding payment obligations. Failure to comply may result in legal action.",
            type="critical",
        )
        db.add(notif)
        vendor.verification_notes = f"Notice sent by admin. {note or ''}"

    elif action == "freeze":
        vendor.profile_status = "suspended"
        vendor.verification_notes = f"Account frozen by admin. {note or 'All marketplace activity halted'}"
        # Cancel all open listings for this vendor
        open_listings = db.query(MarketplaceListing).filter(
            MarketplaceListing.vendor_id == vendor_id,
            MarketplaceListing.status == "open",
        ).all()
        for lst in open_listings:
            lst.status = "cancelled"
        notif = Notification(
            user_id=vendor.user_id,
            title="❄️ Account Frozen",
            message=f"Your account and all open listings have been frozen. Reason: {note or 'Admin action'}. Contact support.",
            type="critical",
        )
        db.add(notif)

    elif action == "unfreeze":
        vendor.profile_status = "verified"
        vendor.verification_notes = f"Account unfrozen by admin. {note or ''}"
        notif = Notification(
            user_id=vendor.user_id,
            title="✅ Account Unfrozen",
            message="Your account has been restored. You may resume marketplace activity.",
            type="info",
        )
        db.add(notif)

    elif action == "reinstate":
        vendor.blacklisted = False
        vendor.blacklisted_at = None
        vendor.blacklist_reason = None
        vendor.profile_status = "verified"
        vendor.verification_notes = f"Reinstated by admin. {note or ''}"
        notif = Notification(
            user_id=vendor.user_id,
            title="✅ Account Reinstated",
            message="Your blacklist has been lifted and your account is now active again.",
            type="info",
        )
        db.add(notif)

    elif action == "clear_penalty":
        vendor.penalty_amount = 0
        vendor.penalty_reason = None
        vendor.verification_notes = f"Penalty cleared by admin. {note or ''}"

    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid action. Use: suspend, approve, warn, blacklist, impose_penalty, send_notice, freeze, unfreeze, reinstate, clear_penalty",
        )

    # Log activity
    entry = ActivityLog(
        entity_type="vendor",
        entity_id=vendor_id,
        action=f"admin_{action}",
        description=f"Admin {action} on vendor {vendor.full_name}. {note or ''}",
        user_id=current_user.id,
    )
    db.add(entry)
    db.commit()

    return {
        "message": f"Action '{action}' applied to vendor {vendor.full_name}",
        "new_status": vendor.profile_status,
        "blacklisted": getattr(vendor, 'blacklisted', False),
        "penalty_amount": getattr(vendor, 'penalty_amount', 0),
    }

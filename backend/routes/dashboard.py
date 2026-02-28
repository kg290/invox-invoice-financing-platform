"""
Dashboard routes — analytics endpoints for vendor and lender dashboards.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func as sa_func
from datetime import datetime, timedelta, timezone
import json

from database import get_db
from models import (
    Vendor, Invoice, InvoiceItem, MarketplaceListing, Lender,
    BlockchainBlock, VerificationCheck, RepaymentSchedule, ActivityLog, User,
    FractionalInvestment,
)
from routes.auth import get_current_user
from routes.vendor import calculate_risk_score_breakdown

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


# ═══════════════════════════════════════════════
#  VENDOR DASHBOARD
# ═══════════════════════════════════════════════

@router.get("/vendor/{vendor_id}")
def vendor_dashboard(vendor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get comprehensive dashboard stats for a vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # ── Invoice stats ──
    invoices = db.query(Invoice).filter(Invoice.vendor_id == vendor_id).all()
    total_invoices = len(invoices)
    total_invoice_value = sum(i.grand_total for i in invoices)
    paid_invoices = sum(1 for i in invoices if i.payment_status == "paid")
    overdue_invoices = sum(1 for i in invoices if i.invoice_status == "overdue")
    draft_invoices = sum(1 for i in invoices if i.invoice_status == "draft")
    listed_invoices = sum(1 for i in invoices if i.is_listed)

    # ── Invoice status distribution (for pie chart) ──
    status_dist = {}
    for inv in invoices:
        status_dist[inv.invoice_status] = status_dist.get(inv.invoice_status, 0) + 1

    # ── Marketplace stats ──
    listings = db.query(MarketplaceListing).filter(MarketplaceListing.vendor_id == vendor_id).all()
    total_listings = len(listings)
    funded_listings = [l for l in listings if l.listing_status == "funded"]
    settled_listings = [l for l in listings if l.listing_status == "settled"]
    partially_funded_listings = [l for l in listings if l.listing_status == "partially_funded"]
    total_funded = sum(l.total_funded_amount or l.funded_amount or 0 for l in funded_listings + settled_listings + partially_funded_listings)
    total_settled = sum(l.total_funded_amount or l.funded_amount or 0 for l in settled_listings)
    open_listings = sum(1 for l in listings if l.listing_status in ("open", "partially_funded"))

    # ── Repayment stats ──
    listing_ids = [l.id for l in listings]
    repayments = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.listing_id.in_(listing_ids)
    ).all() if listing_ids else []
    pending_repayment = sum(r.total_amount for r in repayments if r.status == "pending")
    paid_repayment = sum(r.paid_amount or 0 for r in repayments if r.status == "paid")
    overdue_repayments = sum(1 for r in repayments if r.status == "overdue")

    # ── Monthly trend (last 6 months) ──
    monthly_trend = []
    now = datetime.now(timezone.utc)
    for i in range(5, -1, -1):
        month_start = (now - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            month_end = (now - timedelta(days=30 * (i - 1))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            month_end = now

        month_invoices = [inv for inv in invoices if inv.created_at and month_start <= inv.created_at.replace(tzinfo=timezone.utc if inv.created_at.tzinfo is None else inv.created_at.tzinfo) < month_end]
        month_funded = [l for l in funded_listings + settled_listings if l.funded_at and month_start <= l.funded_at.replace(tzinfo=timezone.utc if l.funded_at.tzinfo is None else l.funded_at.tzinfo) < month_end]

        monthly_trend.append({
            "month": month_start.strftime("%b %Y"),
            "invoices": len(month_invoices),
            "invoice_value": sum(inv.grand_total for inv in month_invoices),
            "funded": sum(l.funded_amount or 0 for l in month_funded),
        })

    # ── Verification summary ──
    checks = db.query(VerificationCheck).filter(VerificationCheck.vendor_id == vendor_id).all()
    verification_summary = {
        "total_checks": len(checks),
        "passed": sum(1 for c in checks if c.status == "passed"),
        "failed": sum(1 for c in checks if c.status == "failed"),
        "warning": sum(1 for c in checks if c.status == "warning"),
        "pending": sum(1 for c in checks if c.status == "pending"),
    }

    # ── Recent activity ──
    activities = db.query(ActivityLog).filter(
        ActivityLog.entity_type == "vendor",
        ActivityLog.entity_id == vendor_id,
    ).order_by(ActivityLog.created_at.desc()).limit(10).all()

    # Also get invoice-related activities
    invoice_ids = [i.id for i in invoices]
    if invoice_ids:
        inv_activities = db.query(ActivityLog).filter(
            ActivityLog.entity_type == "invoice",
            ActivityLog.entity_id.in_(invoice_ids),
        ).order_by(ActivityLog.created_at.desc()).limit(5).all()
        activities = sorted(activities + inv_activities, key=lambda a: a.created_at or datetime.min, reverse=True)[:10]

    recent_activity = [{
        "id": a.id,
        "action": a.action,
        "description": a.description,
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in activities]

    # ── Risk score breakdown ──
    vendor_data = {
        "cibil_score": vendor.cibil_score or 300,
        "gst_compliance_status": vendor.gst_compliance_status or "Irregular",
        "total_gst_filings": vendor.total_gst_filings or 0,
        "year_of_establishment": vendor.year_of_establishment or 2024,
        "annual_turnover": vendor.annual_turnover or 0,
        "existing_liabilities": vendor.existing_liabilities or 0,
        "business_assets_value": vendor.business_assets_value or 0,
    }
    risk_breakdown = calculate_risk_score_breakdown(vendor_data)

    # Use calculated risk score (sum of breakdown factors) — not the stale vendor.risk_score field
    calculated_risk_score = risk_breakdown.get("total_score", vendor.risk_score)

    # Keep vendor DB field in sync
    if vendor.risk_score != calculated_risk_score:
        vendor.risk_score = calculated_risk_score
        db.commit()

    return {
        "vendor": {
            "id": vendor.id,
            "name": vendor.full_name,
            "business_name": vendor.business_name,
            "profile_status": vendor.profile_status,
            "risk_score": calculated_risk_score,
            "cibil_score": vendor.cibil_score,
        },
        "invoices": {
            "total": total_invoices,
            "total_value": round(total_invoice_value, 2),
            "paid": paid_invoices,
            "overdue": overdue_invoices,
            "draft": draft_invoices,
            "listed": listed_invoices,
            "status_distribution": status_dist,
        },
        "marketplace": {
            "total_listings": total_listings,
            "open": open_listings,
            "funded_count": len(funded_listings),
            "settled_count": len(settled_listings),
            "total_funded": round(total_funded, 2),
            "total_settled": round(total_settled, 2),
        },
        "repayment": {
            "pending_amount": round(pending_repayment, 2),
            "paid_amount": round(paid_repayment, 2),
            "overdue_installments": overdue_repayments,
        },
        "verification": verification_summary,
        "monthly_trend": monthly_trend,
        "recent_activity": recent_activity,
        "risk_breakdown": risk_breakdown,
    }


# ═══════════════════════════════════════════════
#  LENDER DASHBOARD
# ═══════════════════════════════════════════════

@router.get("/lender/{lender_id}")
def lender_dashboard(lender_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get comprehensive dashboard stats for a lender."""
    lender = db.query(Lender).filter(Lender.id == lender_id).first()
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")

    # ── Funded listings (legacy + fractional) ──
    # Get listings where this lender has fractional investments
    frac_listing_ids = db.query(FractionalInvestment.listing_id).filter(
        FractionalInvestment.lender_id == lender_id,
        FractionalInvestment.status == "active",
    ).distinct().all()
    frac_listing_ids = [r[0] for r in frac_listing_ids]

    # Also include legacy single-lender funded listings
    legacy_funded = db.query(MarketplaceListing).filter(
        MarketplaceListing.lender_id == lender_id,
        MarketplaceListing.listing_status.in_(["funded", "settled"]),
    ).all()
    legacy_ids = [l.id for l in legacy_funded]

    # Merge both sets
    all_listing_ids = list(set(frac_listing_ids + legacy_ids))
    funded = db.query(MarketplaceListing).filter(
        MarketplaceListing.id.in_(all_listing_ids),
    ).all() if all_listing_ids else []

    # Calculate totals using fractional investments for accuracy
    frac_investments = db.query(FractionalInvestment).filter(
        FractionalInvestment.lender_id == lender_id,
        FractionalInvestment.status == "active",
    ).all()

    total_investments = len(funded)
    total_funded_amount = sum(f.invested_amount for f in frac_investments) if frac_investments else sum(l.funded_amount or 0 for l in funded)
    active_investments = sum(1 for l in funded if l.listing_status in ("funded", "partially_funded"))
    settled_investments = sum(1 for l in funded if l.listing_status == "settled")

    # ── Returns calculation ──
    total_interest_earned = 0
    for l in funded:
        if l.funded_amount and l.max_interest_rate and l.repayment_period_days:
            interest = (l.funded_amount * l.max_interest_rate / 100) * (l.repayment_period_days / 365)
            if l.listing_status == "settled":
                total_interest_earned += interest

    # ── Portfolio risk distribution (multi-factor) ──
    # Compute risk based on actual credit factors: CIBIL score, GST compliance,
    # repayment track record, invoice size relative to turnover
    risk_dist = {"low": 0, "medium": 0, "high": 0}
    for l in funded:
        vendor = db.query(Vendor).filter(Vendor.id == l.vendor_id).first()
        if not vendor:
            risk_dist["medium"] += 1
            continue

        # Factor 1: CIBIL Score (0-40 points)   — 750+ = 40, 650-750 = 25, <650 = 10
        cibil = vendor.cibil_score or 650
        cibil_pts = 40 if cibil >= 750 else (25 if cibil >= 650 else 10)

        # Factor 2: GST Compliance (0-20 points) — active = 20, irregular = 10, lapsed = 0
        gst_status = (vendor.gst_compliance_status or "").lower()
        gst_pts = 20 if "active" in gst_status or "compliant" in gst_status else (10 if gst_status else 0)

        # Factor 3: Repayment history (0-25 points)
        sched_items = db.query(RepaymentSchedule).filter(RepaymentSchedule.listing_id == l.id).all()
        paid = sum(1 for s in sched_items if s.status == "paid")
        total_inst = len(sched_items) if sched_items else 1
        repay_pts = round(25 * (paid / total_inst)) if total_inst > 0 else 12

        # Factor 4: Business maturity (0-15 points) — years in business
        yrs = (datetime.now().year - (vendor.year_of_establishment or 2020))
        biz_pts = min(15, yrs * 3)  # 5+ yrs = full 15

        credit_score = cibil_pts + gst_pts + repay_pts + biz_pts  # 0-100

        if credit_score >= 65:
            risk_dist["low"] += 1
        elif credit_score >= 40:
            risk_dist["medium"] += 1
        else:
            risk_dist["high"] += 1

    # ── Business type distribution ──
    biz_type_dist = {}
    for l in funded:
        vendor = db.query(Vendor).filter(Vendor.id == l.vendor_id).first()
        if vendor:
            btype = vendor.business_type or "Other"
            biz_type_dist[btype] = biz_type_dist.get(btype, 0) + 1

    # ── Available listings (not yet fully funded) ──
    available = db.query(MarketplaceListing).filter(
        MarketplaceListing.listing_status.in_(["open", "partially_funded"])
    ).count()
    available_value = db.query(sa_func.coalesce(sa_func.sum(MarketplaceListing.requested_amount), 0)).filter(
        MarketplaceListing.listing_status.in_(["open", "partially_funded"])
    ).scalar()

    # ── Repayment tracking ──
    listing_ids = [l.id for l in funded]
    repayments = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.listing_id.in_(listing_ids)
    ).all() if listing_ids else []
    upcoming_repayments = [r for r in repayments if r.status == "pending"]
    upcoming_repayments.sort(key=lambda r: r.due_date)
    next_repayments = [{
        "listing_id": r.listing_id,
        "installment": r.installment_number,
        "due_date": r.due_date,
        "amount": r.total_amount,
    } for r in upcoming_repayments[:5]]

    # ── Monthly funding trend ──
    monthly_trend = []
    now = datetime.now(timezone.utc)
    for i in range(5, -1, -1):
        month_start = (now - timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if i > 0:
            month_end = (now - timedelta(days=30 * (i - 1))).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            month_end = now

        month_funded = [l for l in funded if l.funded_at and month_start <= l.funded_at.replace(tzinfo=timezone.utc if l.funded_at.tzinfo is None else l.funded_at.tzinfo) < month_end]
        month_settled = [l for l in funded if l.listing_status == "settled" and l.settlement_date and month_start <= l.settlement_date.replace(tzinfo=timezone.utc if l.settlement_date.tzinfo is None else l.settlement_date.tzinfo) < month_end]

        monthly_trend.append({
            "month": month_start.strftime("%b %Y"),
            "funded": sum(l.funded_amount or 0 for l in month_funded),
            "settled": sum(l.funded_amount or 0 for l in month_settled),
            "count": len(month_funded),
        })

    # ── Recent activity ──
    activities = db.query(ActivityLog).filter(
        ActivityLog.entity_type == "lender",
        ActivityLog.entity_id == lender_id,
    ).order_by(ActivityLog.created_at.desc()).limit(10).all()

    if listing_ids:
        listing_activities = db.query(ActivityLog).filter(
            ActivityLog.entity_type == "listing",
            ActivityLog.entity_id.in_(listing_ids),
        ).order_by(ActivityLog.created_at.desc()).limit(5).all()
        activities = sorted(activities + listing_activities, key=lambda a: a.created_at or datetime.min, reverse=True)[:10]

    recent_activity = [{
        "id": a.id,
        "action": a.action,
        "description": a.description,
        "entity_type": a.entity_type,
        "entity_id": a.entity_id,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    } for a in activities]

    return {
        "lender": {
            "id": lender.id,
            "name": lender.name,
            "organization": lender.organization,
            "lender_type": lender.lender_type,
        },
        "portfolio": {
            "total_investments": total_investments,
            "total_funded": round(total_funded_amount, 2),
            "active_investments": active_investments,
            "settled_investments": settled_investments,
            "total_returns": round(total_interest_earned, 2),
            "roi_percent": round((total_interest_earned / total_funded_amount * 100), 2) if total_funded_amount > 0 else 0,
        },
        "wallet": {
            "balance": round(lender.wallet_balance or 0, 2),
            "escrow_locked": round(lender.escrow_locked or 0, 2),
            "total_withdrawn": round(getattr(lender, 'total_withdrawn', 0) or 0, 2),
        },
        "available_market": {
            "listings_count": available,
            "total_value": round(float(available_value), 2),
        },
        "risk_distribution": risk_dist,
        "business_type_distribution": biz_type_dist,
        "monthly_trend": monthly_trend,
        "upcoming_repayments": next_repayments,
        "recent_activity": recent_activity,
    }

"""
InvoX Pay — Custom Payment Gateway
====================================
A self-hosted payment gateway replacing Razorpay.
Supports card, UPI, and net-banking payment methods.

Flow:
  Frontend  → POST /api/payments/create-funding-order   → Gets order_id
  Frontend  → Opens InvoX Pay Checkout UI (custom React component)
  User      → Enters payment details in the checkout UI
  Frontend  → POST /api/payments/process                → Validates & returns payment_id + signature
  Frontend  → POST /api/payments/verify                 → Backend verifies signature & processes
"""

import os
import json
import hmac
import hashlib
import uuid
import re
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from database import get_db
from models import (
    Payment, MarketplaceListing, RepaymentSchedule, Invoice,
    Lender, Vendor, User, Notification, ActivityLog, BlockchainBlock,
    FractionalInvestment,
)
from blockchain import add_block
from routes.auth import get_current_user

router = APIRouter(prefix="/api/payments", tags=["payments"])

# ── InvoX Pay signing secret ──
INVOX_PAY_SECRET = os.getenv("INVOX_PAY_SECRET", "invox_pay_secret_k4x9m2p7q1w8e5")


# ═══════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════

def _generate_order_id() -> str:
    return f"invox_ord_{uuid.uuid4().hex[:16]}"


def _generate_payment_id() -> str:
    return f"invox_pay_{uuid.uuid4().hex[:16]}"


def _generate_signature(order_id: str, payment_id: str) -> str:
    message = f"{order_id}|{payment_id}"
    return hmac.new(
        INVOX_PAY_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _verify_signature(order_id: str, payment_id: str, signature: str) -> bool:
    expected = _generate_signature(order_id, payment_id)
    return hmac.compare_digest(expected, signature)


def _validate_card(card_number: str) -> bool:
    digits = re.sub(r'\D', '', card_number)
    if len(digits) < 13 or len(digits) > 19:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def _validate_upi(upi_id: str) -> bool:
    return bool(re.match(r'^[\w.\-]+@[\w]+$', upi_id))


# ═══════════════════════════════════════════════
#  SCHEMAS
# ═══════════════════════════════════════════════

class CreateFundingOrderRequest(BaseModel):
    listing_id: int
    lender_id: int
    funded_amount: float = Field(..., gt=0)
    offered_interest_rate: float = Field(..., gt=0, le=100)


class CreateRepaymentOrderRequest(BaseModel):
    listing_id: int
    installment_id: int


class ProcessPaymentRequest(BaseModel):
    order_id: str
    payment_method: str  # card, upi, netbanking
    card_number: Optional[str] = None
    card_expiry: Optional[str] = None
    card_cvv: Optional[str] = None
    card_holder: Optional[str] = None
    upi_id: Optional[str] = None
    bank_code: Optional[str] = None


class VerifyPaymentRequest(BaseModel):
    order_id: str
    payment_id: str
    signature: str


class RefundRequest(BaseModel):
    listing_id: int
    reason: str = "Lender requested refund"


class PayAllRemainingRequest(BaseModel):
    listing_id: int


class GatewayConfigResponse(BaseModel):
    gateway_name: str = "InvoX Pay"
    currency: str = "INR"
    company_name: str = "InvoX"
    description: str = "Invoice Financing Platform"
    supported_methods: list = ["card", "upi", "netbanking"]
    supported_banks: list = [
        {"code": "SBI", "name": "State Bank of India"},
        {"code": "HDFC", "name": "HDFC Bank"},
        {"code": "ICICI", "name": "ICICI Bank"},
        {"code": "AXIS", "name": "Axis Bank"},
        {"code": "KOTAK", "name": "Kotak Mahindra Bank"},
        {"code": "BOB", "name": "Bank of Baroda"},
        {"code": "PNB", "name": "Punjab National Bank"},
        {"code": "YES", "name": "Yes Bank"},
    ]


# ═══════════════════════════════════════════════
#  GET CONFIG
# ═══════════════════════════════════════════════

@router.get("/config")
def get_gateway_config():
    """Return gateway config for the frontend."""
    return GatewayConfigResponse()


# ═══════════════════════════════════════════════
#  CREATE ORDER — FUNDING (Lender pays to fund invoice)
# ═══════════════════════════════════════════════

@router.post("/create-funding-order")
def create_funding_order(
    data: CreateFundingOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an InvoX Pay order for invoice funding (supports fractional/Community Pot)."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == data.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.listing_status not in ("open", "partially_funded"):
        raise HTTPException(status_code=400, detail=f"Listing is '{listing.listing_status}', not open for funding")
    remaining = listing.requested_amount - (listing.total_funded_amount or 0)
    if data.funded_amount > remaining + 0.01:
        raise HTTPException(status_code=400, detail=f"Amount exceeds remaining ₹{remaining:,.0f}")
    if data.offered_interest_rate > listing.max_interest_rate:
        raise HTTPException(status_code=400, detail=f"Interest rate ({data.offered_interest_rate}%) exceeds max ({listing.max_interest_rate}%)")

    lender = db.query(Lender).filter(Lender.id == data.lender_id).first()
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")

    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
    order_id = _generate_order_id()

    payment = Payment(
        gateway_order_id=order_id,
        amount=data.funded_amount,
        status="created",
        payment_type="funding",
        listing_id=listing.id,
        user_id=current_user.id,
        payer_name=lender.name,
        payer_email=lender.email,
        notes_json=json.dumps({
            "lender_id": lender.id,
            "offered_interest_rate": data.offered_interest_rate,
            "invoice_number": invoice.invoice_number if invoice else "",
        }),
    )
    db.add(payment)
    db.commit()

    return {
        "order_id": order_id,
        "amount": data.funded_amount,
        "amount_paise": int(data.funded_amount * 100),
        "currency": "INR",
        "listing_id": listing.id,
        "payer_name": lender.name,
        "payer_email": lender.email,
        "description": f"Fund Invoice {invoice.invoice_number if invoice else listing.id}",
        "gateway": "invox_pay",
    }


# ═══════════════════════════════════════════════
#  CREATE ORDER — REPAYMENT (Vendor pays installment)
# ═══════════════════════════════════════════════

@router.post("/create-repayment-order")
def create_repayment_order(
    data: CreateRepaymentOrderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an InvoX Pay order for repayment installment."""
    sched = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.id == data.installment_id,
        RepaymentSchedule.listing_id == data.listing_id,
    ).first()
    if not sched:
        raise HTTPException(status_code=404, detail="Installment not found")
    if sched.status == "paid":
        raise HTTPException(status_code=400, detail="Installment already paid")

    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == data.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()
    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
    order_id = _generate_order_id()

    payment = Payment(
        gateway_order_id=order_id,
        amount=sched.total_amount,
        status="created",
        payment_type="repayment",
        listing_id=data.listing_id,
        installment_id=sched.id,
        user_id=current_user.id,
        payer_name=vendor.full_name if vendor else current_user.name,
        payer_email=vendor.email if vendor else current_user.email,
        notes_json=json.dumps({
            "installment_number": sched.installment_number,
            "principal": sched.principal_amount,
            "interest": sched.interest_amount,
        }),
    )
    db.add(payment)
    db.commit()

    return {
        "order_id": order_id,
        "amount": sched.total_amount,
        "amount_paise": int(sched.total_amount * 100),
        "currency": "INR",
        "listing_id": data.listing_id,
        "installment_number": sched.installment_number,
        "payer_name": vendor.full_name if vendor else current_user.name,
        "payer_email": vendor.email if vendor else "",
        "description": f"Repayment #{sched.installment_number} for Invoice {invoice.invoice_number if invoice else ''}",
        "gateway": "invox_pay",
    }


# ═══════════════════════════════════════════════
#  PROCESS PAYMENT (validates details, generates payment credentials)
# ═══════════════════════════════════════════════

@router.post("/process")
def process_payment(
    data: ProcessPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process payment through InvoX Pay gateway."""
    payment = db.query(Payment).filter(Payment.gateway_order_id == data.order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Order not found")
    if payment.status == "paid":
        raise HTTPException(status_code=400, detail="Payment already completed")

    # Validate payment method
    if data.payment_method == "card":
        if not data.card_number or not data.card_expiry or not data.card_cvv or not data.card_holder:
            raise HTTPException(status_code=400, detail="All card details are required")
        if not _validate_card(data.card_number):
            raise HTTPException(status_code=400, detail="Invalid card number")
        if not re.match(r'^\d{2}/\d{2}$', data.card_expiry):
            raise HTTPException(status_code=400, detail="Invalid expiry format. Use MM/YY")
        month, year = data.card_expiry.split("/")
        if int(month) < 1 or int(month) > 12:
            raise HTTPException(status_code=400, detail="Invalid expiry month")
        if len(data.card_cvv) not in [3, 4]:
            raise HTTPException(status_code=400, detail="Invalid CVV")
    elif data.payment_method == "upi":
        if not data.upi_id:
            raise HTTPException(status_code=400, detail="UPI ID is required")
        if not _validate_upi(data.upi_id):
            raise HTTPException(status_code=400, detail="Invalid UPI ID format (e.g., name@upi)")
    elif data.payment_method == "netbanking":
        if not data.bank_code:
            raise HTTPException(status_code=400, detail="Bank selection is required")
    else:
        raise HTTPException(status_code=400, detail="Invalid payment method")

    payment_id = _generate_payment_id()
    signature = _generate_signature(data.order_id, payment_id)

    payment.payment_method = data.payment_method
    db.commit()

    return {
        "success": True,
        "order_id": data.order_id,
        "payment_id": payment_id,
        "signature": signature,
        "amount": payment.amount,
        "currency": payment.currency,
        "payment_method": data.payment_method,
        "gateway": "invox_pay",
        "message": "Payment processed successfully",
    }


# ═══════════════════════════════════════════════
#  VERIFY PAYMENT — Processes funding or repayment
# ═══════════════════════════════════════════════

@router.post("/verify")
def verify_payment(
    data: VerifyPaymentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify InvoX Pay payment signature and process the transaction."""
    payment = db.query(Payment).filter(Payment.gateway_order_id == data.order_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment record not found")
    if payment.status == "paid":
        return {"message": "Payment already processed", "status": "paid"}

    if not _verify_signature(data.order_id, data.payment_id, data.signature):
        payment.status = "failed"
        db.commit()
        raise HTTPException(status_code=400, detail="Payment signature verification failed")

    payment.gateway_payment_id = data.payment_id
    payment.gateway_signature = data.signature
    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)

    if payment.payment_type == "funding":
        result = _process_funding_payment(payment, db)
    elif payment.payment_type == "repayment":
        result = _process_repayment_payment(payment, db)
    elif payment.payment_type == "repayment_all":
        result = _process_pay_all_payment(payment, db)
    else:
        db.commit()
        result = {"message": "Payment verified"}

    return {
        "message": "Payment verified and processed successfully",
        "status": "paid",
        "payment_id": data.payment_id,
        "type": payment.payment_type,
        **result,
    }


def _process_funding_payment(payment: Payment, db: Session) -> dict:
    """Process a verified funding payment — creates fractional investment, updates listing (Community Pot)."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == payment.listing_id).first()
    if not listing:
        db.commit()
        return {"warning": "Listing not found"}

    notes = json.loads(payment.notes_json) if payment.notes_json else {}
    lender_id = notes.get("lender_id")
    offered_interest_rate = float(notes.get("offered_interest_rate", 12))

    lender = db.query(Lender).filter(Lender.id == lender_id).first() if lender_id else None
    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()

    # ── Create FractionalInvestment record ──
    ownership_pct = round((payment.amount / listing.requested_amount) * 100, 2)
    expected_return = round((payment.amount * offered_interest_rate / 100) * (listing.repayment_period_days / 365), 2)

    block_data = {
        "type": "fractional_funding",
        "listing_id": listing.id,
        "invoice_number": invoice.invoice_number if invoice else "",
        "lender_id": lender.id if lender else None,
        "lender_name": lender.name if lender else payment.payer_name,
        "funded_amount": payment.amount,
        "ownership_pct": ownership_pct,
        "offered_interest_rate": offered_interest_rate,
        "payment_id": payment.gateway_payment_id,
        "gateway": "invox_pay",
        "funded_at": datetime.now(timezone.utc).isoformat(),
    }
    block = add_block(db, "funding", block_data)

    frac = FractionalInvestment(
        listing_id=listing.id,
        lender_id=lender.id if lender else None,
        user_id=payment.user_id,
        invested_amount=payment.amount,
        offered_interest_rate=offered_interest_rate,
        ownership_percentage=ownership_pct,
        expected_return=expected_return,
        payment_id=payment.gateway_payment_id,
        blockchain_hash=block.block_hash,
        status="active",
    )
    db.add(frac)

    # ── Update listing aggregates ──
    new_total = (listing.total_funded_amount or 0) + payment.amount
    listing.total_funded_amount = round(new_total, 2)
    listing.total_investors = (listing.total_investors or 0) + 1

    fully_funded = new_total >= listing.requested_amount - 0.01
    num_installments = 0

    if fully_funded:
        listing.listing_status = "funded"
        listing.funded_amount = round(new_total, 2)
        listing.funded_at = datetime.now(timezone.utc)
        if listing.total_investors == 1:
            listing.lender_id = lender.id if lender else None
            listing.funded_by = lender.name if lender else payment.payer_name
        else:
            listing.funded_by = f"{listing.total_investors} investors"

        # Generate repayment schedule with weighted average rate
        all_fracs = db.query(FractionalInvestment).filter(
            FractionalInvestment.listing_id == listing.id,
            FractionalInvestment.status == "active",
        ).all()
        total_weighted_rate = sum(f.invested_amount * f.offered_interest_rate for f in all_fracs)
        avg_rate = total_weighted_rate / new_total if new_total > 0 else offered_interest_rate

        num_installments = max(1, listing.repayment_period_days // 30)
        principal_per = round(new_total / num_installments, 2)
        annual_rate = avg_rate / 100

        for i in range(1, num_installments + 1):
            due = datetime.now(timezone.utc) + timedelta(days=30 * i)
            interest_amt = round((new_total * annual_rate * 30) / 365, 2)
            sched = RepaymentSchedule(
                listing_id=listing.id,
                installment_number=i,
                due_date=due.strftime("%Y-%m-%d"),
                principal_amount=principal_per,
                interest_amount=interest_amt,
                total_amount=round(principal_per + interest_amt, 2),
                status="pending",
            )
            db.add(sched)

        vendor_user = db.query(User).filter(User.vendor_id == listing.vendor_id).first()
        if vendor_user:
            db.add(Notification(
                user_id=vendor_user.id,
                title="Invoice Fully Funded! 🎉",
                message=f"Your invoice has been fully funded ₹{new_total:,.0f} by {listing.total_investors} investor(s) via InvoX Pay. Repayment in {num_installments} installments.",
                notification_type="funding",
                link=f"/vendor/{listing.vendor_id}/invoices",
            ))
    else:
        listing.listing_status = "partially_funded"
        vendor_user = db.query(User).filter(User.vendor_id == listing.vendor_id).first()
        if vendor_user:
            pct = round(new_total / listing.requested_amount * 100, 1)
            db.add(Notification(
                user_id=vendor_user.id,
                title="New Investment Received! 💰",
                message=f"{lender.name if lender else payment.payer_name} invested ₹{payment.amount:,.0f} via InvoX Pay ({pct}% funded, {listing.total_investors} investor(s)).",
                notification_type="funding",
                link=f"/vendor/{listing.vendor_id}/invoices",
            ))

    lender_user = db.query(User).filter(User.lender_id == lender.id).first() if lender else None
    if lender_user:
        db.add(Notification(
            user_id=lender_user.id,
            title="Investment Confirmed ✅",
            message=f"₹{payment.amount:,.0f} ({ownership_pct}% ownership) confirmed for invoice {invoice.invoice_number if invoice else ''}. Expected return: ₹{expected_return:,.0f}.",
            notification_type="funding",
            link=f"/marketplace/{listing.id}",
        ))

    db.add(ActivityLog(
        entity_type="listing", entity_id=listing.id,
        action="fractional_funded",
        description=f"₹{payment.amount:,.0f} invested via InvoX Pay by {lender.name if lender else payment.payer_name} ({ownership_pct}% slice)",
        metadata_json=json.dumps({
            "payment_id": payment.gateway_payment_id,
            "amount": payment.amount,
            "ownership_pct": ownership_pct,
            "total_funded": new_total,
            "total_investors": listing.total_investors,
            "gateway": "invox_pay",
        }),
    ))

    db.commit()
    return {
        "invested_amount": payment.amount,
        "ownership_percentage": ownership_pct,
        "expected_return": expected_return,
        "lender": lender.name if lender else payment.payer_name,
        "blockchain_hash": block.block_hash,
        "total_funded_amount": listing.total_funded_amount,
        "total_investors": listing.total_investors,
        "funding_progress_pct": round(new_total / listing.requested_amount * 100, 1),
        "fully_funded": fully_funded,
        "installments": num_installments if fully_funded else 0,
    }


def _process_repayment_payment(payment: Payment, db: Session) -> dict:
    """Process a verified repayment payment — marks installment as paid, auto-settles if all paid."""
    sched = db.query(RepaymentSchedule).filter(RepaymentSchedule.id == payment.installment_id).first()
    if not sched:
        db.commit()
        return {"warning": "Installment not found"}

    sched.status = "paid"
    sched.paid_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sched.paid_amount = sched.total_amount

    block_data = {
        "type": "repayment",
        "listing_id": payment.listing_id,
        "installment": sched.installment_number,
        "amount": sched.total_amount,
        "payment_id": payment.gateway_payment_id,
        "gateway": "invox_pay",
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }
    add_block(db, "repayment", block_data)

    remaining = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.listing_id == payment.listing_id,
        RepaymentSchedule.status != "paid",
    ).count()

    auto_settled = False
    if remaining == 0:
        listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == payment.listing_id).first()
        if listing and listing.listing_status == "funded":
            listing.listing_status = "settled"
            listing.settlement_date = datetime.now(timezone.utc)
            invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
            if invoice:
                invoice.payment_status = "paid"
                invoice.invoice_status = "paid"
            add_block(db, "settlement", {
                "type": "auto_settlement",
                "listing_id": payment.listing_id,
                "payment_id": payment.gateway_payment_id,
                "gateway": "invox_pay",
                "settled_at": datetime.now(timezone.utc).isoformat(),
            })
            auto_settled = True

    db.add(ActivityLog(
        entity_type="listing", entity_id=payment.listing_id,
        action="repayment",
        description=f"Installment #{sched.installment_number} paid ₹{sched.total_amount:,.0f} via InvoX Pay",
        metadata_json=json.dumps({
            "payment_id": payment.gateway_payment_id,
            "installment": sched.installment_number,
            "gateway": "invox_pay",
        }),
    ))

    db.commit()
    return {
        "installment_number": sched.installment_number,
        "remaining": remaining,
        "auto_settled": auto_settled,
    }


def _process_pay_all_payment(payment: Payment, db: Session) -> dict:
    """Process a verified pay-all payment — marks ALL unpaid installments as paid, auto-settles."""
    notes = json.loads(payment.notes_json) if payment.notes_json else {}
    installment_ids = notes.get("installment_ids", [])

    unpaid = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.listing_id == payment.listing_id,
        RepaymentSchedule.status != "paid",
    ).all()

    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for sched in unpaid:
        sched.status = "paid"
        sched.paid_date = now_str
        sched.paid_amount = sched.total_amount

    # Blockchain record
    add_block(db, "repayment_all", {
        "type": "repayment_all",
        "listing_id": payment.listing_id,
        "total_amount": payment.amount,
        "installments_paid": len(unpaid),
        "payment_id": payment.gateway_payment_id,
        "gateway": "invox_pay",
        "paid_at": datetime.now(timezone.utc).isoformat(),
    })

    # Auto-settle the listing
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == payment.listing_id).first()
    auto_settled = False
    if listing and listing.listing_status == "funded":
        listing.listing_status = "settled"
        listing.settlement_date = datetime.now(timezone.utc)
        invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
        if invoice:
            invoice.payment_status = "paid"
            invoice.invoice_status = "paid"
        add_block(db, "settlement", {
            "type": "auto_settlement",
            "listing_id": payment.listing_id,
            "payment_id": payment.gateway_payment_id,
            "gateway": "invox_pay",
            "settled_at": datetime.now(timezone.utc).isoformat(),
        })
        auto_settled = True

    db.add(ActivityLog(
        entity_type="listing", entity_id=payment.listing_id,
        action="repayment_all",
        description=f"All {len(unpaid)} remaining installments paid at once ₹{payment.amount:,.0f} via InvoX Pay",
        metadata_json=json.dumps({
            "payment_id": payment.gateway_payment_id,
            "installments_paid": len(unpaid),
            "total_amount": payment.amount,
            "gateway": "invox_pay",
        }),
    ))

    # Notify lender about full repayment
    if listing and listing.lender_id:
        lender_user = db.query(User).filter(User.lender_id == listing.lender_id).first()
        if lender_user:
            db.add(Notification(
                user_id=lender_user.id,
                title="Full Repayment Received 🎉",
                message=f"All {len(unpaid)} installments totalling ₹{payment.amount:,.0f} have been paid in full.",
                notification_type="settlement",
                link=f"/marketplace/{listing.id}",
            ))

    db.commit()
    return {
        "installments_paid": len(unpaid),
        "total_amount": payment.amount,
        "auto_settled": auto_settled,
    }


# ═══════════════════════════════════════════════
#  PAYMENT HISTORY
# ═══════════════════════════════════════════════

@router.get("/history")
def get_payment_history(
    listing_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get payment history, optionally filtered by listing."""
    q = db.query(Payment).filter(Payment.status == "paid")
    if listing_id:
        q = q.filter(Payment.listing_id == listing_id)
    else:
        q = q.filter(Payment.user_id == current_user.id)

    payments = q.order_by(Payment.paid_at.desc()).all()
    return [{
        "id": p.id,
        "order_id": p.gateway_order_id,
        "payment_id": p.gateway_payment_id,
        "amount": p.amount,
        "currency": p.currency,
        "status": p.status,
        "payment_type": p.payment_type,
        "payment_method": p.payment_method,
        "listing_id": p.listing_id,
        "installment_id": p.installment_id,
        "payer_name": p.payer_name,
        "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        "gateway": "invox_pay",
    } for p in payments]


# ═══════════════════════════════════════════════
#  REFUND — Lender gets money back
# ═══════════════════════════════════════════════

@router.post("/refund")
def refund_payment(
    data: RefundRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process a refund for a funded listing. Returns money to the lender."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == data.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.listing_status not in ("funded",):
        raise HTTPException(status_code=400, detail=f"Cannot refund — listing is '{listing.listing_status}', must be 'funded'")

    # Check no installments have been paid yet (can only refund if no repayment started)
    paid_installments = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.listing_id == listing.id,
        RepaymentSchedule.status == "paid",
    ).count()
    if paid_installments > 0:
        raise HTTPException(status_code=400, detail="Cannot refund — repayment has already started. Contact support for partial refund.")

    # Find the original funding payment
    funding_payment = db.query(Payment).filter(
        Payment.listing_id == listing.id,
        Payment.payment_type == "funding",
        Payment.status == "paid",
    ).first()
    if not funding_payment:
        raise HTTPException(status_code=404, detail="Original funding payment not found")

    # Create refund payment record
    refund_order_id = _generate_order_id()
    refund_payment_id = _generate_payment_id()
    refund_signature = _generate_signature(refund_order_id, refund_payment_id)

    refund = Payment(
        gateway_order_id=refund_order_id,
        gateway_payment_id=refund_payment_id,
        gateway_signature=refund_signature,
        amount=funding_payment.amount,
        status="refunded",
        payment_type="refund",
        payment_method=funding_payment.payment_method,
        listing_id=listing.id,
        user_id=current_user.id,
        payer_name=funding_payment.payer_name,
        payer_email=funding_payment.payer_email,
        paid_at=datetime.now(timezone.utc),
        notes_json=json.dumps({
            "reason": data.reason,
            "original_payment_id": funding_payment.gateway_payment_id,
            "original_order_id": funding_payment.gateway_order_id,
        }),
    )
    db.add(refund)

    # Mark original payment as refunded
    funding_payment.status = "refunded"

    # Reset listing back to open
    listing.listing_status = "open"
    listing.funded_amount = None
    listing.funded_by = None
    listing.lender_id = None
    listing.funded_at = None

    # Delete all pending installments for this listing
    db.query(RepaymentSchedule).filter(
        RepaymentSchedule.listing_id == listing.id,
    ).delete()

    # Record on blockchain
    block = add_block(db, "refund", {
        "type": "refund",
        "listing_id": listing.id,
        "refund_amount": funding_payment.amount,
        "reason": data.reason,
        "original_payment_id": funding_payment.gateway_payment_id,
        "refunded_at": datetime.now(timezone.utc).isoformat(),
    })

    # Notify lender
    lender_user = None
    if listing.lender_id:
        lender_user = db.query(User).filter(User.lender_id == listing.lender_id).first()
    if lender_user:
        db.add(Notification(
            user_id=lender_user.id,
            title="Refund Processed 💸",
            message=f"Your investment of ₹{funding_payment.amount:,.0f} has been refunded. Reason: {data.reason}",
            notification_type="refund",
            link=f"/marketplace/{listing.id}",
        ))

    # Notify vendor
    vendor_user = db.query(User).filter(User.vendor_id == listing.vendor_id).first()
    if vendor_user:
        db.add(Notification(
            user_id=vendor_user.id,
            title="Funding Refunded ⚠️",
            message=f"The funding of ₹{funding_payment.amount:,.0f} has been refunded to the lender. Your invoice is now open for funding again.",
            notification_type="refund",
            link=f"/marketplace/{listing.id}",
        ))

    # Activity log
    db.add(ActivityLog(
        entity_type="listing", entity_id=listing.id,
        action="refund",
        description=f"Funding of ₹{funding_payment.amount:,.0f} refunded. Reason: {data.reason}",
        metadata_json=json.dumps({
            "refund_payment_id": refund_payment_id,
            "original_payment_id": funding_payment.gateway_payment_id,
            "amount": funding_payment.amount,
            "reason": data.reason,
        }),
    ))

    db.commit()

    return {
        "message": "Refund processed successfully",
        "refund_amount": funding_payment.amount,
        "refund_payment_id": refund_payment_id,
        "blockchain_hash": block.block_hash,
        "listing_status": "open",
    }


# ═══════════════════════════════════════════════
#  PAY ALL REMAINING — Pay all unpaid installments at once
# ═══════════════════════════════════════════════

@router.post("/create-pay-all-order")
def create_pay_all_order(
    data: PayAllRemainingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an InvoX Pay order to pay all remaining installments at once."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == data.listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing.listing_status != "funded":
        raise HTTPException(status_code=400, detail="Listing is not in funded status")

    unpaid = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.listing_id == data.listing_id,
        RepaymentSchedule.status != "paid",
    ).all()

    if not unpaid:
        raise HTTPException(status_code=400, detail="All installments already paid")

    total_amount = sum(s.total_amount for s in unpaid)
    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()
    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
    order_id = _generate_order_id()

    payment = Payment(
        gateway_order_id=order_id,
        amount=total_amount,
        status="created",
        payment_type="repayment_all",
        listing_id=data.listing_id,
        user_id=current_user.id,
        payer_name=vendor.full_name if vendor else current_user.name,
        payer_email=vendor.email if vendor else current_user.email,
        notes_json=json.dumps({
            "installment_ids": [s.id for s in unpaid],
            "installment_count": len(unpaid),
            "individual_amounts": [s.total_amount for s in unpaid],
        }),
    )
    db.add(payment)
    db.commit()

    return {
        "order_id": order_id,
        "amount": total_amount,
        "amount_paise": int(total_amount * 100),
        "currency": "INR",
        "listing_id": data.listing_id,
        "installment_count": len(unpaid),
        "payer_name": vendor.full_name if vendor else current_user.name,
        "payer_email": vendor.email if vendor else "",
        "description": f"Pay all remaining ({len(unpaid)}) installments for Invoice {invoice.invoice_number if invoice else ''}",
        "gateway": "invox_pay",
    }

"""
Auto-Repayment via NPCI e-Mandate (Simulated)
══════════════════════════════════════════════════
Simulates NPCI NACH e-Mandate registration and auto-debit execution
for loan repayment. In production, this integrates with:
  - NPCI e-NACH API for mandate registration
  - Partner bank APIs for debit execution
  - BBPS for payment status tracking

Workflow:
  1. Vendor registers e-Mandate → bank authorization
  2. On repayment date, system auto-executes debit
  3. Failed debits retry with exponential backoff
  4. Mandate can be paused/revoked by vendor
"""

import uuid
import json
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    EMandateRegistration, EMandateExecution,
    RepaymentSchedule, MarketplaceListing, Vendor,
)


# ═══════════════════════════════════════════════
#  MANDATE REGISTRATION
# ═══════════════════════════════════════════════

def register_mandate(
    db: Session,
    vendor_id: int,
    max_amount: float,
    frequency: str = "monthly",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict:
    """Register a new e-Mandate for auto-repayment."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise ValueError("Vendor not found")

    if not vendor.bank_account_number or not vendor.bank_ifsc:
        raise ValueError("Vendor bank details incomplete. Cannot register mandate.")

    if frequency not in ("weekly", "monthly", "quarterly", "as_presented"):
        raise ValueError(f"Invalid frequency: {frequency}")

    # Check for existing active mandate
    existing = db.query(EMandateRegistration).filter(
        EMandateRegistration.vendor_id == vendor_id,
        EMandateRegistration.mandate_status == "active",
    ).first()
    if existing:
        raise ValueError(f"Active mandate already exists (ID: {existing.id}). Revoke it first.")

    # Generate NPCI mandate reference (simulated UMRN)
    mandate_ref = f"INVX-NACH-{uuid.uuid4().hex[:12].upper()}"

    now = datetime.now(timezone.utc)
    s_date = datetime.fromisoformat(start_date) if start_date else now
    e_date = datetime.fromisoformat(end_date) if end_date else now + timedelta(days=365)

    mandate = EMandateRegistration(
        vendor_id=vendor_id,
        mandate_reference=mandate_ref,
        bank_account_number=vendor.bank_account_number,
        bank_ifsc=vendor.bank_ifsc,
        bank_name=vendor.bank_name,
        max_amount=max_amount,
        frequency=frequency,
        start_date=s_date,
        end_date=e_date,
        mandate_status="active",  # In production: "pending" until bank confirms
        npci_response_json=json.dumps({
            "umrn": mandate_ref,
            "status": "ACCEPTED",
            "bank_ref": f"REF-{uuid.uuid4().hex[:8].upper()}",
            "accepted_at": now.isoformat(),
            "note": "Simulated NPCI e-NACH acceptance",
        }),
    )
    db.add(mandate)
    db.commit()
    db.refresh(mandate)

    return {
        "mandate_id": mandate.id,
        "mandate_reference": mandate_ref,
        "vendor_id": vendor_id,
        "bank_account": f"****{vendor.bank_account_number[-4:]}" if vendor.bank_account_number else None,
        "bank_ifsc": vendor.bank_ifsc,
        "max_amount": max_amount,
        "frequency": frequency,
        "start_date": s_date.isoformat(),
        "end_date": e_date.isoformat(),
        "status": "active",
        "message": "e-Mandate registered successfully. Auto-debit is now enabled.",
    }


# ═══════════════════════════════════════════════
#  MANDATE MANAGEMENT
# ═══════════════════════════════════════════════

def get_mandate(db: Session, mandate_id: int) -> dict:
    """Get mandate details."""
    m = db.query(EMandateRegistration).filter(EMandateRegistration.id == mandate_id).first()
    if not m:
        raise ValueError("Mandate not found")

    executions = db.query(EMandateExecution).filter(
        EMandateExecution.mandate_id == mandate_id
    ).order_by(EMandateExecution.executed_at.desc()).limit(10).all()

    return {
        "mandate_id": m.id,
        "mandate_reference": m.mandate_reference,
        "vendor_id": m.vendor_id,
        "bank_account": f"****{m.bank_account_number[-4:]}" if m.bank_account_number else None,
        "bank_ifsc": m.bank_ifsc,
        "max_amount": m.max_amount,
        "frequency": m.frequency,
        "status": m.mandate_status,
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "end_date": m.end_date.isoformat() if m.end_date else None,
        "recent_executions": [{
            "execution_id": e.id,
            "amount": e.amount,
            "status": e.execution_status,
            "executed_at": e.executed_at.isoformat() if e.executed_at else None,
            "retry_count": e.retry_count,
        } for e in executions],
    }


def pause_mandate(db: Session, mandate_id: int) -> dict:
    """Pause an active mandate (vendor-initiated)."""
    m = db.query(EMandateRegistration).filter(EMandateRegistration.id == mandate_id).first()
    if not m:
        raise ValueError("Mandate not found")
    if m.mandate_status != "active":
        raise ValueError(f"Cannot pause mandate in '{m.mandate_status}' status")

    m.mandate_status = "paused"
    db.commit()
    return {"mandate_id": mandate_id, "status": "paused", "message": "Mandate paused. Auto-debits suspended."}


def resume_mandate(db: Session, mandate_id: int) -> dict:
    """Resume a paused mandate."""
    m = db.query(EMandateRegistration).filter(EMandateRegistration.id == mandate_id).first()
    if not m:
        raise ValueError("Mandate not found")
    if m.mandate_status != "paused":
        raise ValueError(f"Cannot resume mandate in '{m.mandate_status}' status")

    m.mandate_status = "active"
    db.commit()
    return {"mandate_id": mandate_id, "status": "active", "message": "Mandate resumed. Auto-debits re-enabled."}


def revoke_mandate(db: Session, mandate_id: int) -> dict:
    """Permanently revoke a mandate."""
    m = db.query(EMandateRegistration).filter(EMandateRegistration.id == mandate_id).first()
    if not m:
        raise ValueError("Mandate not found")
    if m.mandate_status in ("revoked", "expired"):
        raise ValueError(f"Mandate already {m.mandate_status}")

    m.mandate_status = "revoked"
    db.commit()
    return {"mandate_id": mandate_id, "status": "revoked", "message": "Mandate permanently revoked."}


# ═══════════════════════════════════════════════
#  AUTO-DEBIT EXECUTION
# ═══════════════════════════════════════════════

def execute_auto_debit(db: Session, mandate_id: int, installment_id: int) -> dict:
    """
    Execute a single auto-debit against a mandate for a repayment installment.
    In production, this calls NPCI NACH debit API.
    """
    mandate = db.query(EMandateRegistration).filter(EMandateRegistration.id == mandate_id).first()
    if not mandate:
        raise ValueError("Mandate not found")
    if mandate.mandate_status != "active":
        raise ValueError(f"Mandate is '{mandate.mandate_status}', not active")

    installment = db.query(RepaymentSchedule).filter(RepaymentSchedule.id == installment_id).first()
    if not installment:
        raise ValueError("Installment not found")
    if installment.status == "paid":
        raise ValueError("Installment already paid")

    if installment.amount > mandate.max_amount:
        raise ValueError(f"Amount ₹{installment.amount} exceeds mandate limit ₹{mandate.max_amount}")

    # Check mandate validity dates
    now = datetime.now(timezone.utc)
    if mandate.end_date and now > mandate.end_date:
        mandate.mandate_status = "expired"
        db.commit()
        raise ValueError("Mandate has expired")

    # Simulate NPCI debit execution (90% success rate in simulation)
    import random
    success = random.random() < 0.90

    exec_ref = f"EXEC-{uuid.uuid4().hex[:10].upper()}"

    execution = EMandateExecution(
        mandate_id=mandate_id,
        installment_id=installment_id,
        execution_reference=exec_ref,
        amount=installment.amount,
        execution_status="success" if success else "failed",
        retry_count=0,
        max_retries=3,
        bank_response_json=json.dumps({
            "txn_ref": exec_ref,
            "status": "SUCCESS" if success else "INSUFFICIENT_FUNDS",
            "bank_ref": f"BNK-{uuid.uuid4().hex[:8].upper()}",
            "timestamp": now.isoformat(),
        }),
    )
    db.add(execution)

    if success:
        installment.status = "paid"
        installment.paid_date = now.strftime("%Y-%m-%d")
        installment.paid_amount = installment.amount

        # Check if all installments for this listing are paid
        listing_id = installment.listing_id
        remaining = db.query(RepaymentSchedule).filter(
            RepaymentSchedule.listing_id == listing_id,
            RepaymentSchedule.status != "paid",
            RepaymentSchedule.id != installment_id,
        ).count()
        if remaining == 0:
            listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
            if listing:
                listing.listing_status = "settled"

    db.commit()
    db.refresh(execution)

    result = {
        "execution_id": execution.id,
        "execution_reference": exec_ref,
        "mandate_id": mandate_id,
        "installment_id": installment_id,
        "amount": installment.amount,
        "status": execution.execution_status,
    }

    if not success:
        result["message"] = "Auto-debit failed. Will retry automatically."
        result["next_retry"] = (now + timedelta(hours=24)).isoformat()

    return result


def retry_failed_debits(db: Session) -> dict:
    """
    Batch retry all failed auto-debits that haven't exceeded max retries.
    This would be called by a scheduled cron job.
    """
    failed_executions = db.query(EMandateExecution).filter(
        EMandateExecution.execution_status == "failed",
        EMandateExecution.retry_count < EMandateExecution.max_retries,
    ).all()

    results = {"retried": 0, "succeeded": 0, "failed_again": 0, "max_retries_reached": 0}

    import random
    for exec_record in failed_executions:
        mandate = db.query(EMandateRegistration).filter(
            EMandateRegistration.id == exec_record.mandate_id,
            EMandateRegistration.mandate_status == "active",
        ).first()
        if not mandate:
            continue

        exec_record.retry_count += 1
        results["retried"] += 1

        # Simulated retry (higher success on retry)
        success = random.random() < (0.80 + exec_record.retry_count * 0.05)

        if success:
            exec_record.execution_status = "success"
            results["succeeded"] += 1

            installment = db.query(RepaymentSchedule).filter(
                RepaymentSchedule.id == exec_record.installment_id
            ).first()
            if installment:
                installment.status = "paid"
                installment.paid_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                installment.paid_amount = installment.amount
        else:
            if exec_record.retry_count >= exec_record.max_retries:
                exec_record.execution_status = "retrying"
                results["max_retries_reached"] += 1
            else:
                results["failed_again"] += 1

    db.commit()
    return results


def get_vendor_mandates(db: Session, vendor_id: int) -> list[dict]:
    """Get all mandates for a vendor."""
    mandates = db.query(EMandateRegistration).filter(
        EMandateRegistration.vendor_id == vendor_id
    ).order_by(EMandateRegistration.created_at.desc()).all()

    return [{
        "mandate_id": m.id,
        "mandate_reference": m.mandate_reference,
        "status": m.mandate_status,
        "max_amount": m.max_amount,
        "frequency": m.frequency,
        "bank_account": f"****{m.bank_account_number[-4:]}" if m.bank_account_number else None,
        "start_date": m.start_date.isoformat() if m.start_date else None,
        "end_date": m.end_date.isoformat() if m.end_date else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    } for m in mandates]

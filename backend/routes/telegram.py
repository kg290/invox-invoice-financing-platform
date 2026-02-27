"""
Telegram Bot integration routes.

Endpoints:
  POST /api/telegram/login               — Bot authenticates user with email + password, links chat_id
  POST /api/telegram/generate-link-code  — Generate a 6-digit code (legacy)
  POST /api/telegram/verify-link-code    — Bot verifies 6-digit code (legacy)
  GET  /api/telegram/status-by-chat/{chat_id} — Bot lookup by chat_id
  GET  /api/telegram/invoices-by-chat/{chat_id} — Bot invoice list by chat_id
  POST /api/telegram/upload              — Bot file upload (invoice image/PDF) + trigger OCR
  PATCH /api/invoices/{id}/ocr-result    — Receive OCR extraction results and update invoice
"""
import os
import json
import secrets
import logging
import random
import bcrypt
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, UploadFile
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from database import get_db
from models import User, Vendor, Invoice, InvoiceItem, Notification
from routes.auth import get_current_user

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ══════════════════════════════════════════════════════
#  SCHEMAS
# ══════════════════════════════════════════════════════

class TelegramLoginRequest(BaseModel):
    email: str
    password: str
    chat_id: str
    telegram_username: Optional[str] = None


class GenerateLinkCodeResponse(BaseModel):
    link_code: str
    expires_in_seconds: int
    message: str


class VerifyLinkCodeRequest(BaseModel):
    code: str
    chat_id: str
    telegram_username: Optional[str] = None


class OCRResultPayload(BaseModel):
    ocr_status: str = "ocr_done"
    ocr_confidence: Optional[float] = None
    ocr_raw_text: Optional[str] = None
    ocr_warnings: Optional[str] = None
    invoice_number: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_gstin: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    grand_total: Optional[float] = None
    seller_name: Optional[str] = None
    seller_gstin: Optional[str] = None
    line_items: Optional[list] = None


# ══════════════════════════════════════════════════════
#  1. TELEGRAM LOGIN — bot authenticates user via email + password
# ══════════════════════════════════════════════════════

@router.post("/login")
def telegram_login(data: TelegramLoginRequest, db: Session = Depends(get_db)):
    """
    Bot-facing endpoint: authenticate via email + password and link chat_id to user.
    Returns user info on success so the bot can show the main menu.
    """
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not _verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")

    # Link telegram chat_id to this user
    user.telegram_chat_id = data.chat_id
    user.telegram_username = data.telegram_username
    db.commit()

    return {
        "message": "Login successful — account linked",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "vendor_id": user.vendor_id,
    }


# ══════════════════════════════════════════════════════
#  2. GENERATE LINK CODE — (legacy, kept for web dashboard)
# ══════════════════════════════════════════════════════

@router.post("/generate-link-code", response_model=GenerateLinkCodeResponse)
def generate_link_code(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Generate a 6-digit code that the user sends to the Telegram bot for linking.
    Valid for 10 minutes.
    """
    code = str(random.randint(100000, 999999))
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    current_user.telegram_link_code = code
    current_user.telegram_link_code_expires = expires_at
    db.commit()

    return GenerateLinkCodeResponse(
        link_code=code,
        expires_in_seconds=600,
        message=f"Send this code to the InvoX Telegram bot to link your account.",
    )


# ══════════════════════════════════════════════════════
#  3. VERIFY LINK CODE — (legacy)
# ══════════════════════════════════════════════════════

@router.post("/verify-link-code")
def verify_link_code(data: VerifyLinkCodeRequest, db: Session = Depends(get_db)):
    """
    Bot-facing endpoint: verify the 6-digit code and link chat_id to the user.
    Returns user info on success.
    """
    user = db.query(User).filter(User.telegram_link_code == data.code).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid code")

    if user.telegram_link_code_expires and datetime.now(timezone.utc) > user.telegram_link_code_expires.replace(
        tzinfo=timezone.utc if user.telegram_link_code_expires.tzinfo is None else user.telegram_link_code_expires.tzinfo
    ):
        user.telegram_link_code = None
        user.telegram_link_code_expires = None
        db.commit()
        raise HTTPException(status_code=400, detail="Code expired. Generate a new one from the dashboard.")

    # Link telegram
    user.telegram_chat_id = data.chat_id
    user.telegram_username = data.telegram_username
    user.telegram_link_code = None
    user.telegram_link_code_expires = None
    db.commit()

    return {
        "message": "Account linked successfully",
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "vendor_id": user.vendor_id,
    }


# ══════════════════════════════════════════════════════
#  3. STATUS BY CHAT — bot lookup
# ══════════════════════════════════════════════════════

@router.get("/status-by-chat/{chat_id}")
def status_by_chat(chat_id: str, db: Session = Depends(get_db)):
    """Look up a user by their Telegram chat_id."""
    user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account linked to this chat_id")
    return {
        "user_id": user.id,
        "name": user.name,
        "email": user.email,
        "role": user.role,
        "vendor_id": user.vendor_id,
        "telegram_username": user.telegram_username,
    }


# ══════════════════════════════════════════════════════
#  4. INVOICES BY CHAT — bot list invoices
# ══════════════════════════════════════════════════════

@router.get("/invoices-by-chat/{chat_id}")
def invoices_by_chat(chat_id: str, db: Session = Depends(get_db)):
    """Return the 5 most recent invoices for the user linked to this chat_id."""
    user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="No account linked to this chat_id")

    inv_list = (
        db.query(Invoice)
        .filter(Invoice.vendor_id == user.vendor_id)
        .order_by(Invoice.created_at.desc())
        .limit(5)
        .all()
    ) if user.vendor_id else []

    return {
        "invoices": [
            {
                "id": inv.id,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date,
                "due_date": inv.due_date,
                "grand_total": inv.grand_total,
                "invoice_status": inv.invoice_status,
                "payment_status": inv.payment_status,
                "ocr_status": getattr(inv, "ocr_status", None),
            }
            for inv in inv_list
        ]
    }


# ══════════════════════════════════════════════════════
#  5. UPLOAD — bot sends invoice file, triggers OCR
# ══════════════════════════════════════════════════════

@router.post("/upload")
async def upload_via_telegram(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Accept a file upload from the Telegram bot. Creates a draft invoice and triggers OCR."""
    form = await request.form()
    chat_id = form.get("chat_id", "")
    upload_file = form.get("file")

    if not chat_id or not upload_file:
        raise HTTPException(status_code=422, detail="chat_id and file are required")

    user = db.query(User).filter(User.telegram_chat_id == str(chat_id)).first()
    if not user:
        raise HTTPException(status_code=401, detail="No account linked to this chat_id")

    if not user.vendor_id:
        raise HTTPException(status_code=400, detail="No vendor profile linked. Complete your KYC first.")

    file_name = upload_file.filename or f"tg_upload_{chat_id}.bin"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, file_name)

    contents = await upload_file.read()
    with open(save_path, "wb") as f:
        f.write(contents)

    # Create a draft invoice
    new_inv = Invoice(
        vendor_id=user.vendor_id,
        invoice_number=f"TG-{secrets.token_hex(4).upper()}",
        invoice_date=datetime.now().strftime("%Y-%m-%d"),
        due_date=datetime.now().strftime("%Y-%m-%d"),
        supply_type="intra_state",
        place_of_supply="Maharashtra",
        place_of_supply_code="27",
        buyer_name="Pending OCR...",
        buyer_address="Pending OCR...",
        buyer_city="Pending",
        buyer_state="Maharashtra",
        buyer_state_code="27",
        buyer_pincode="000000",
        invoice_status="draft",
        ocr_status="processing",
        file_path=os.path.abspath(save_path),
        source="telegram",
    )
    db.add(new_inv)
    db.commit()
    db.refresh(new_inv)

    # Trigger OCR in background thread
    abs_path = os.path.abspath(save_path)
    background_tasks.add_task(_run_ocr_sync, new_inv.id, abs_path)
    logger.info(f"OCR background task queued for invoice {new_inv.id}, file: {abs_path}")

    # Log notification
    notif = Notification(
        user_id=user.id,
        title="Invoice Received via Telegram",
        message=f"File '{file_name}' uploaded. OCR processing started...",
        notification_type="system",
    )
    db.add(notif)
    db.commit()

    return {
        "message": f"File '{file_name}' stored and OCR started.",
        "file_name": file_name,
        "user_id": user.id,
        "invoice_id": new_inv.id,
    }


def _run_ocr_sync(invoice_id: int, file_path: str):
    """Run OCR synchronously — called by FastAPI BackgroundTasks."""
    try:
        from services.ocr_service import run_ocr_and_update
        logger.info(f"[OCR] Starting background OCR for invoice {invoice_id}")
        run_ocr_and_update(invoice_id, file_path)
        logger.info(f"[OCR] Completed for invoice {invoice_id}")
    except Exception as e:
        logger.error(f"[OCR] Failed for invoice {invoice_id}: {e}", exc_info=True)


# ══════════════════════════════════════════════════════
#  6. OCR RESULT PATCH — update invoice with OCR data
# ══════════════════════════════════════════════════════

@router.patch("/invoices/{invoice_id}/ocr-result")
def patch_ocr_result(
    invoice_id: int,
    data: OCRResultPayload,
    db: Session = Depends(get_db),
):
    """Update an invoice with OCR extraction results."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    inv.ocr_status = data.ocr_status
    if data.ocr_confidence is not None:
        inv.ocr_confidence = data.ocr_confidence
    if data.ocr_raw_text is not None:
        inv.ocr_raw_text = data.ocr_raw_text[:5000]  # truncate
    if data.ocr_warnings is not None:
        inv.ocr_warnings = data.ocr_warnings

    # Update invoice fields if OCR extracted them
    if data.invoice_number and data.invoice_number != "UNKNOWN-001":
        # Check uniqueness
        existing = db.query(Invoice).filter(
            Invoice.invoice_number == data.invoice_number,
            Invoice.id != invoice_id
        ).first()
        if not existing:
            inv.invoice_number = data.invoice_number

    if data.buyer_name and data.buyer_name != "Unknown Buyer":
        inv.buyer_name = data.buyer_name
    if data.buyer_gstin:
        inv.buyer_gstin = data.buyer_gstin
    if data.invoice_date:
        inv.invoice_date = data.invoice_date
    if data.due_date:
        inv.due_date = data.due_date
    if data.grand_total and data.grand_total > 0:
        inv.grand_total = data.grand_total

    # Create line items from OCR
    if data.line_items:
        for idx, item_data in enumerate(data.line_items):
            item = InvoiceItem(
                invoice_id=invoice_id,
                item_number=idx + 1,
                description=item_data.get("description", "OCR Item"),
                hsn_sac_code=item_data.get("hsn_sac_code", "0000"),
                quantity=item_data.get("quantity", 1),
                unit=item_data.get("unit", "NOS"),
                unit_price=item_data.get("unit_price", 0),
                discount_percent=0,
                discount_amount=0,
                taxable_value=item_data.get("total", 0),
                gst_rate=item_data.get("gst_rate", 18),
                total_amount=item_data.get("total", 0),
            )
            db.add(item)

    db.commit()
    return {"message": "Invoice updated with OCR results", "invoice_id": invoice_id}


# ══════════════════════════════════════════════════════
#  7. UNLINK TELEGRAM
# ══════════════════════════════════════════════════════

@router.delete("/unlink")
def unlink_telegram(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove Telegram link from the current user's account."""
    current_user.telegram_chat_id = None
    current_user.telegram_username = None
    db.commit()
    return {"message": "Telegram account unlinked"}

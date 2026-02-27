"""
Telegram Bot integration routes.

Endpoints:
  POST /api/telegram/webhook          - Receives all Telegram updates
  POST /api/telegram/link             - Generate a one-time account-link token
  POST /api/telegram/confirm-link     - Bot calls this to store chat_id
  GET  /api/telegram/status/{user_id} - Check if a user has linked Telegram
  POST /api/telegram/send-test        - Send a test message to a linked user
  GET  /api/telegram/status-by-chat/{chat_id} - Bot lookup by chat_id
  GET  /api/telegram/invoices-by-chat/{chat_id} - Bot invoice list
  POST /api/telegram/upload           - Bot file upload
  POST /api/telegram/create-vendor    - Bot creates minimal vendor during onboarding
"""
import os
import json
import secrets
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from models import User, Vendor, Invoice, Notification
from routes.auth import get_current_user
from services.telegram_service import (
    send_telegram_message,
    build_notification_message,
)

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

# In-memory token store: token -> {user_id, expires_at}
_link_tokens: dict = {}

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════
#  SCHEMAS
# ══════════════════════════════════════════════════════

class LinkTokenResponse(BaseModel):
    token: str
    deep_link: str
    bot_username: str
    expires_in_seconds: int


class ConfirmLinkRequest(BaseModel):
    token: str
    chat_id: str
    telegram_username: Optional[str] = None


class SendTestRequest(BaseModel):
    user_id: int
    message: str = "👋 Hello from InvoX! Your Telegram is connected."


class TelegramVendorCreate(BaseModel):
    """Minimal vendor creation from Telegram bot onboarding."""
    chat_id: str
    business_name: str
    gstin: str
    pan: str
    bank_account: str
    ifsc: str
    industry: str


# ══════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════

def _get_bot_username() -> str:
    return os.environ.get("TELEGRAM_BOT_USERNAME", "InvoXBot")


def _purge_expired_tokens():
    now = datetime.now(timezone.utc)
    expired = [t for t, v in _link_tokens.items() if v["expires_at"] < now]
    for t in expired:
        del _link_tokens[t]


async def _handle_telegram_update(update: dict, db: Session):
    """Process a single Telegram update object."""
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = str(message["chat"]["id"])
    text = message.get("text", "")
    from_user = message.get("from", {})
    username = from_user.get("username", "")
    first_name = from_user.get("first_name", "InvoX User")

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    api_base = f"https://api.telegram.org/bot{token}"

    async def reply(msg: str, parse_mode: str = "HTML"):
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(f"{api_base}/sendMessage", json={
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": parse_mode,
            })

    # ── /start ──
    if text.startswith("/start"):
        parts = text.split(" ", 1)
        link_token = parts[1].strip() if len(parts) > 1 else None

        if link_token and link_token in _link_tokens:
            entry = _link_tokens[link_token]
            if entry["expires_at"] > datetime.now(timezone.utc):
                user = db.query(User).filter(User.id == entry["user_id"]).first()
                if user:
                    user.telegram_chat_id = chat_id
                    user.telegram_username = username
                    db.commit()
                    del _link_tokens[link_token]
                    await reply(
                        f"✅ <b>Account linked successfully!</b>\n\n"
                        f"Hi {user.name}, your InvoX account is now connected to Telegram.\n\n"
                        f"You'll receive notifications and OTPs here.\n\n"
                        f"Type /help to see what I can do!"
                    )
                    return

        await reply(
            f"👋 <b>Welcome to InvoX Bot!</b>\n\n"
            f"Hi {first_name}! I'm your InvoX assistant.\n\n"
            f"📄 <b>What I can do:</b>\n"
            f"• Send invoice upload confirmations\n"
            f"• Deliver OTPs for secure login\n"
            f"• Notify you about funding & settlements\n\n"
            f"🔗 <b>To get started, link your account:</b>\n"
            f"Go to InvoX → Settings → Connect Telegram\n"
            f"Then use the link button or send /link <token>\n\n"
            f"Type /help for all commands."
        )
        return

    # ── /link <token> ──
    if text.startswith("/link"):
        parts = text.split(" ", 1)
        if len(parts) < 2 or not parts[1].strip():
            await reply(
                "⚠️ Please provide your link token.\n"
                "Usage: <code>/link YOUR_TOKEN</code>\n\n"
                "Get your token from the InvoX app under Settings → Connect Telegram."
            )
            return

        link_token = parts[1].strip()
        _purge_expired_tokens()

        if link_token not in _link_tokens:
            await reply(
                "❌ <b>Invalid or expired token.</b>\n\n"
                "Please generate a new token from the InvoX app."
            )
            return

        entry = _link_tokens[link_token]
        if entry["expires_at"] < datetime.now(timezone.utc):
            del _link_tokens[link_token]
            await reply("❌ <b>Token expired.</b> Please generate a new token.")
            return

        user = db.query(User).filter(User.id == entry["user_id"]).first()
        if not user:
            await reply("❌ User account not found.")
            return

        user.telegram_chat_id = chat_id
        user.telegram_username = username
        db.commit()
        del _link_tokens[link_token]

        await reply(
            f"✅ <b>Account linked successfully!</b>\n\n"
            f"Hi {user.name}! Your InvoX account is now connected.\n\n"
            f"You'll receive notifications and OTPs here.\n"
            f"Type /help to see all commands."
        )
        return

    # ── /status ──
    if text.startswith("/status"):
        user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
        if user:
            await reply(
                f"✅ <b>Linked Account</b>\n\n"
                f"👤 Name: {user.name}\n"
                f"📧 Email: {user.email}\n"
                f"🎭 Role: {user.role.capitalize()}"
            )
        else:
            await reply(
                "⚠️ <b>No account linked.</b>\n\n"
                "Use /link <token> or the InvoX app to connect your account."
            )
        return

    # ── /invoices ──
    if text.startswith("/invoices"):
        user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
        if not user:
            await reply("⚠️ Please link your account first. See /help")
            return

        invoices = (
            db.query(Invoice)
            .filter(Invoice.vendor_id == user.vendor_id)
            .order_by(Invoice.created_at.desc())
            .limit(5)
            .all()
        ) if user.vendor_id else []

        if not invoices:
            await reply("📭 No invoices found.")
            return

        lines = ["📋 <b>Your Recent Invoices</b>\n"]
        for inv in invoices:
            lines.append(
                f"• <b>#{inv.invoice_number}</b> — ₹{inv.grand_total:,.0f} "
                f"[{inv.invoice_status.upper()}]"
            )
        await reply("\n".join(lines))
        return

    # ── /help ──
    if text.startswith("/help"):
        await reply(
            "ℹ️ <b>InvoX Bot Commands</b>\n\n"
            "/start — Welcome message\n"
            "/link <token> — Link your InvoX account\n"
            "/status — Check linked account\n"
            "/invoices — View your 5 latest invoices\n"
            "/help — Show this message\n\n"
            "📄 <b>Upload documents:</b>\n"
            "Send any PDF/image file and I'll store it in InvoX."
        )
        return

    # ── Document upload ──
    document = message.get("document")
    photo = message.get("photo")
    if document or photo:
        user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
        if not user:
            await reply("⚠️ Please link your account first before uploading. Use /link or see /help.")
            return

        await reply("⏳ Processing your document...")

        try:
            file_id = document["file_id"] if document else photo[-1]["file_id"]
            file_name = document.get("file_name", f"telegram_upload_{chat_id}.jpg") if document else f"photo_{chat_id}.jpg"
            bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

            async with httpx.AsyncClient(timeout=30) as client:
                fpath_resp = await client.get(
                    f"https://api.telegram.org/bot{bot_token}/getFile",
                    params={"file_id": file_id}
                )
                fpath_data = fpath_resp.json()
                if not fpath_data.get("ok"):
                    raise Exception("Failed to get file path")

                tg_file_path = fpath_data["result"]["file_path"]
                file_url = f"https://api.telegram.org/file/bot{bot_token}/{tg_file_path}"

                file_resp = await client.get(file_url)
                file_bytes = file_resp.content

            os.makedirs(UPLOAD_DIR, exist_ok=True)
            save_path = os.path.join(UPLOAD_DIR, file_name)
            with open(save_path, "wb") as f:
                f.write(file_bytes)

            if user.id:
                notif = Notification(
                    user_id=user.id,
                    title="Document Received via Telegram",
                    message=f"File '{file_name}' was uploaded via Telegram bot.",
                    notification_type="system",
                )
                db.add(notif)
                db.commit()

            await reply(
                f"✅ <b>Document saved!</b>\n\n"
                f"📁 File: <code>{file_name}</code>\n"
                f"You can view it in your InvoX dashboard."
            )
        except Exception as exc:
            print(f"[TelegramBot] Document upload error: {exc}")
            await reply("❌ Failed to process your document. Please try again.")
        return

    # Unknown
    await reply(
        "🤖 I didn't understand that. Type /help to see available commands."
    )


# ══════════════════════════════════════════════════════
#  ENDPOINTS
# ══════════════════════════════════════════════════════

@router.post("/webhook")
async def telegram_webhook(request: Request, db: Session = Depends(get_db)):
    """Receive Telegram updates via webhook."""
    try:
        update = await request.json()
        await _handle_telegram_update(update, db)
    except Exception as exc:
        print(f"[TelegramWebhook] Error: {exc}")
    return {"ok": True}


@router.post("/link", response_model=LinkTokenResponse)
def generate_link_token(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate a one-time token the user sends to the bot to link their account."""
    _purge_expired_tokens()

    old_tokens = [t for t, v in _link_tokens.items() if v["user_id"] == current_user.id]
    for t in old_tokens:
        del _link_tokens[t]

    token = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    _link_tokens[token] = {"user_id": current_user.id, "expires_at": expires_at}

    bot_username = _get_bot_username()
    deep_link = f"https://t.me/{bot_username}?start={token}"

    return LinkTokenResponse(
        token=token,
        deep_link=deep_link,
        bot_username=bot_username,
        expires_in_seconds=600,
    )


@router.post("/confirm-link")
def confirm_link(
    data: ConfirmLinkRequest,
    db: Session = Depends(get_db),
):
    """Called by the bot server to confirm account linking."""
    _purge_expired_tokens()

    if data.token not in _link_tokens:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    entry = _link_tokens[data.token]
    if entry["expires_at"] < datetime.now(timezone.utc):
        del _link_tokens[data.token]
        raise HTTPException(status_code=400, detail="Token expired")

    user = db.query(User).filter(User.id == entry["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.telegram_chat_id = data.chat_id
    user.telegram_username = data.telegram_username
    db.commit()
    del _link_tokens[data.token]

    return {"message": "Account linked successfully", "user_id": user.id}


@router.get("/status/{user_id}")
def telegram_status(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check whether a user has linked their Telegram account."""
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorised")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "linked": bool(user.telegram_chat_id),
        "telegram_username": user.telegram_username,
        "chat_id_set": bool(user.telegram_chat_id),
    }


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


@router.post("/send-test")
async def send_test_message(
    data: SendTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Send a test Telegram message to a linked user."""
    if current_user.id != data.user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorised")

    user = db.query(User).filter(User.id == data.user_id).first()
    if not user or not user.telegram_chat_id:
        raise HTTPException(status_code=400, detail="User has not linked a Telegram account")

    success = await send_telegram_message(user.telegram_chat_id, build_notification_message("Test Message", data.message))
    if not success:
        raise HTTPException(status_code=502, detail="Failed to send Telegram message")

    return {"message": "Test message sent"}


# ══════════════════════════════════════════════════════
#  BOT-FACING ENDPOINTS (no auth token required)
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
            }
            for inv in inv_list
        ]
    }


@router.post("/upload")
async def upload_via_telegram(
    request: Request,
    db: Session = Depends(get_db),
):
    """Accept a file upload forwarded from the Telegram bot."""
    from fastapi import UploadFile
    form = await request.form()
    chat_id = form.get("chat_id", "")
    upload_file: UploadFile = form.get("file")  # type: ignore

    if not chat_id or not upload_file:
        raise HTTPException(status_code=422, detail="chat_id and file are required")

    user = db.query(User).filter(User.telegram_chat_id == chat_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="No account linked to this chat_id")

    file_name = upload_file.filename or f"tg_upload_{chat_id}.bin"
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    save_path = os.path.join(UPLOAD_DIR, file_name)

    contents = await upload_file.read()
    with open(save_path, "wb") as f:
        f.write(contents)

    # Create a shell invoice if file is OCR-eligible
    is_ocr_eligible = any(file_name.lower().endswith(ext) for ext in [".pdf", ".jpg", ".jpeg", ".png"])

    invoice_id = None
    if is_ocr_eligible and user.vendor_id:
        new_inv = Invoice(
            vendor_id=user.vendor_id,
            invoice_number=f"TG-{os.urandom(4).hex().upper()}",
            invoice_date=datetime.now().strftime("%Y-%m-%d"),
            due_date=datetime.now().strftime("%Y-%m-%d"),
            supply_type="intra_state",
            place_of_supply="Maharashtra",
            place_of_supply_code="27",
            buyer_name="Pending OCR...",
            buyer_address="Pending OCR...",
            buyer_city="Pending...",
            buyer_state="Maharashtra",
            buyer_state_code="27",
            buyer_pincode="000000",
            invoice_status="draft",
            ocr_status="processing",
            file_path=os.path.abspath(save_path),
        )
        db.add(new_inv)
        db.commit()
        db.refresh(new_inv)
        invoice_id = new_inv.id

        # Trigger OCR service asynchronously
        async def _trigger_ocr(inv_id: int, fpath: str, fname: str):
            ocr_url = os.environ.get("OCR_SERVICE_URL", "http://localhost:8001")
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    with open(fpath, "rb") as fp:
                        files = {"file": (fname, fp, "application/octet-stream")}
                        await client.post(f"{ocr_url}/ocr/extract/{inv_id}", files=files)
            except Exception as e:
                logger.error(f"OCR trigger failed for invoice {inv_id}: {e}")

        import asyncio
        asyncio.ensure_future(_trigger_ocr(invoice_id, os.path.abspath(save_path), file_name))

    # Log notification
    notif = Notification(
        user_id=user.id,
        title="Document Received via Telegram",
        message=f"File '{file_name}' was uploaded via the InvoX Telegram bot." +
                (" Processing with OCR..." if invoice_id else ""),
        notification_type="system",
    )
    db.add(notif)
    db.commit()

    return {
        "message": f"File '{file_name}' stored successfully.",
        "file_name": file_name,
        "user_id": user.id,
        "invoice_id": invoice_id,
    }


class LinkByEmailRequest(BaseModel):
    email: str
    chat_id: str
    telegram_username: Optional[str] = None


@router.post("/link-by-email")
def link_by_email(data: LinkByEmailRequest, db: Session = Depends(get_db)):
    """
    Bot-facing endpoint: link a telegram chat_id to a user found by email.
    Used during bot onboarding when the bot just registered a user.
    """
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.telegram_chat_id = data.chat_id
    user.telegram_username = data.telegram_username
    db.commit()

    return {"message": "Chat ID linked", "user_id": user.id}


@router.post("/create-vendor")
def create_vendor_from_telegram(
    data: TelegramVendorCreate,
    db: Session = Depends(get_db),
):
    """
    Create a minimal Vendor profile from Telegram bot onboarding data.
    This is called by the bot after user registration.
    Returns the vendor_id so the bot can store it.
    """
    # Find the user by chat_id
    user = db.query(User).filter(User.telegram_chat_id == data.chat_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="No user linked to this chat_id")

    # Check if user already has a vendor
    if user.vendor_id:
        return {"vendor_id": user.vendor_id, "message": "Vendor already exists"}

    # Check if GSTIN already exists
    existing = db.query(Vendor).filter(Vendor.gstin == data.gstin.upper()).first()
    if existing:
        # Link existing vendor to this user
        user.vendor_id = existing.id
        db.commit()
        return {"vendor_id": existing.id, "message": "Linked to existing vendor"}

    # Create a minimal vendor with defaults for required fields
    vendor = Vendor(
        full_name=user.name,
        date_of_birth="2000-01-01",
        phone=user.phone or "9999900000",
        email=user.email,
        personal_pan=data.pan.upper(),
        personal_aadhaar="000000000000",  # Placeholder
        address="Via Telegram Bot",
        city="Mumbai",
        state="Maharashtra",
        pincode="400001",
        business_name=data.business_name,
        business_type="Proprietorship",
        business_category=data.industry,
        year_of_establishment=2020,
        business_address="Via Telegram Bot",
        business_city="Mumbai",
        business_state="Maharashtra",
        business_pincode="400001",
        gstin=data.gstin.upper(),
        gst_registration_date="2020-01-01",
        gst_filing_frequency="Quarterly",
        cibil_score=650,
        annual_turnover=500000,
        business_assets_value=100000,
        bank_account_number=data.bank_account,
        bank_name="Bank",
        bank_ifsc=data.ifsc.upper(),
        nominee_name=user.name,
        nominee_relationship="Self",
        nominee_phone=user.phone or "9999900000",
        profile_status="pending",
    )
    db.add(vendor)
    db.flush()

    # Link vendor to user
    user.vendor_id = vendor.id
    db.commit()

    return {"vendor_id": vendor.id, "message": "Vendor created successfully"}

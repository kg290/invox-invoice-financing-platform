"""
Telegram notification service.
Sends messages to users who have linked their Telegram account.
"""
import os
import httpx


def get_bot_token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment")
    return token


async def send_telegram_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to a Telegram chat. Returns True on success."""
    try:
        token = get_bot_token()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": parse_mode,
            })
            data = resp.json()
            if data.get("ok"):
                return True
            print(f"[TelegramService] sendMessage failed: {data}")
            return False
    except Exception as exc:
        print(f"[TelegramService] Error sending message: {exc}")
        return False


def build_otp_message(otp: str, user_name: str) -> str:
    return (
        f"🔐 <b>InvoX Verification Code</b>\n\n"
        f"Hi {user_name},\n\n"
        f"Your one-time password is:\n\n"
        f"<code>{otp}</code>\n\n"
        f"⏱ Valid for <b>5 minutes</b>. Do not share this with anyone."
    )


def build_notification_message(title: str, body: str) -> str:
    return f"🔔 <b>{title}</b>\n\n{body}"


def build_ocr_complete_message(invoice_id: int, confidence: float, invoice_number: str, total: float) -> str:
    return (
        f"✅ <b>Invoice OCR Complete</b>\n\n"
        f"📄 Invoice: <code>{invoice_number}</code>\n"
        f"💰 Total: ₹{total:,.2f}\n"
        f"📊 Confidence: {confidence:.0%}\n\n"
        f"View details on the InvoX dashboard."
    )


def send_telegram_message_sync(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to a Telegram chat (synchronous version for background tasks)."""
    try:
        token = get_bot_token()
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = httpx.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }, timeout=10)
        data = resp.json()
        if data.get("ok"):
            return True
        print(f"[TelegramService] sendMessage failed: {data}")
        return False
    except Exception as exc:
        print(f"[TelegramService] Sync error sending message: {exc}")
        return False

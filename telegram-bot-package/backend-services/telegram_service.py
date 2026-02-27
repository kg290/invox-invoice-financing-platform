"""
Telegram notification service.
Sends messages to users who have linked their Telegram account.
Uses the Bot API sendMessage endpoint directly (no polling/webhook dependency).
"""
import os
import httpx

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}"


def get_bot_token() -> str:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment")
    return token


async def send_telegram_message(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """
    Send a message to a Telegram chat.
    Returns True on success, False on failure.
    """
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


def send_telegram_message_sync(chat_id: str, text: str, parse_mode: str = "HTML") -> bool:
    """
    Synchronous wrapper for environments that don't support async.
    """
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, send_telegram_message(chat_id, text, parse_mode))
                return future.result()
        else:
            return loop.run_until_complete(send_telegram_message(chat_id, text, parse_mode))
    except Exception as exc:
        print(f"[TelegramService] Sync wrapper error: {exc}")
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

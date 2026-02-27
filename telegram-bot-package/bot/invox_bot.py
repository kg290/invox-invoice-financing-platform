"""
InvoX Telegram Bot — Invoice Upload with Email + Password Authentication
=========================================================================
Flow:
  1. User sends /start → bot asks for email
  2. User enters email → bot asks for password
  3. Bot verifies email+password with backend → account linked
  4. Once authenticated, user can upload invoice images/PDFs
  5. Bot sends the file to backend → OCR extracts data → user gets notified

Commands:
  /start   — Start the bot & authenticate
  /upload  — Upload an invoice (must be authenticated)
  /status  — Check linked account info
  /invoices — List recent invoices
  /cancel  — Cancel current flow
  /help    — Show all commands
"""
import os
import logging

import httpx
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes,
    filters,
)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    format="%(asctime)s — %(name)s — %(levelname)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("InvoXBot")

# ══════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Conversation states ──
(
    WAITING_FOR_EMAIL,    # 0 — waiting for email address
    WAITING_FOR_PASSWORD, # 1 — waiting for password
    MAIN_MENU,            # 2 — authenticated, main menu
    UPLOAD_INVOICE,       # 3 — waiting for invoice file
) = range(4)


# ══════════════════════════════════════════════════════
#  API HELPERS
# ══════════════════════════════════════════════════════

async def api_get(path: str) -> dict | None:
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(f"{BACKEND_URL}{path}")
            if r.status_code == 200:
                return r.json()
    except Exception as e:
        logger.error(f"API GET {path}: {e}")
    return None


async def api_post(path: str, payload: dict = None, files=None) -> tuple[int, dict]:
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            if files:
                r = await c.post(f"{BACKEND_URL}{path}", data=payload or {}, files=files)
            else:
                r = await c.post(f"{BACKEND_URL}{path}", json=payload or {})
            return r.status_code, r.json()
    except Exception as e:
        logger.error(f"API POST {path}: {e}")
        return 500, {"detail": str(e)}


async def telegram_login(email: str, password: str, chat_id: str, username: str) -> dict | None:
    """Call backend to authenticate via email+password and link telegram."""
    status, data = await api_post("/api/telegram/login", {
        "email": email,
        "password": password,
        "chat_id": chat_id,
        "telegram_username": username,
    })
    if status == 200:
        return data
    return None


async def check_user_linked(chat_id: str) -> dict | None:
    """Check if a chat_id is already linked to a user."""
    return await api_get(f"/api/telegram/status-by-chat/{chat_id}")


async def get_user_invoices(chat_id: str) -> list:
    """Get invoices for the linked user."""
    data = await api_get(f"/api/telegram/invoices-by-chat/{chat_id}")
    return (data or {}).get("invoices", [])


async def upload_invoice_file(chat_id: str, file_name: str, file_bytes: bytes) -> tuple[int, dict]:
    """Upload an invoice file to the backend."""
    return await api_post(
        "/api/telegram/upload",
        payload={"chat_id": chat_id},
        files={"file": (file_name, file_bytes, "application/octet-stream")},
    )


# ══════════════════════════════════════════════════════
#  /start — ENTRY POINT
# ══════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    first_name = update.effective_user.first_name or "there"

    # Check if already linked
    user_data = await check_user_linked(chat_id)
    if user_data:
        context.user_data["linked_user"] = user_data
        await update.message.reply_text(
            f"👋 Welcome back, <b>{user_data.get('name', first_name)}</b>!\n\n"
            f"✅ Your account is linked.\n\n"
            f"What would you like to do?",
            parse_mode="HTML",
            reply_markup=_main_menu_kb(),
        )
        return MAIN_MENU

    # Not linked — ask for email
    await update.message.reply_text(
        f"👋 <b>Welcome to InvoX Bot!</b>\n\n"
        f"Hi {first_name}! To use this bot, please log in with your InvoX account.\n\n"
        f"📧 <b>Enter your email address:</b>",
        parse_mode="HTML",
    )
    return WAITING_FOR_EMAIL


# ══════════════════════════════════════════════════════
#  EMAIL + PASSWORD VERIFICATION
# ══════════════════════════════════════════════════════

async def handle_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User sent their email address."""
    text = update.message.text.strip()

    # Basic email validation
    if "@" not in text or "." not in text:
        await update.message.reply_text(
            "⚠️ That doesn't look like a valid email.\n\n"
            "📧 <b>Please enter your email address:</b>",
            parse_mode="HTML",
        )
        return WAITING_FOR_EMAIL

    # Store email and ask for password
    context.user_data["login_email"] = text
    await update.message.reply_text(
        f"📧 Email: <code>{text}</code>\n\n"
        f"🔑 <b>Now enter your password:</b>",
        parse_mode="HTML",
    )
    return WAITING_FOR_PASSWORD


async def handle_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User sent their password. Authenticate with backend."""
    chat_id = str(update.effective_chat.id)
    username = update.effective_user.username or ""
    password = update.message.text.strip()
    email = context.user_data.get("login_email", "")

    if not email:
        await update.message.reply_text(
            "⚠️ Something went wrong. Please start again with /start",
        )
        return ConversationHandler.END

    # Delete the password message for security
    try:
        await update.message.delete()
    except Exception:
        pass  # May not have permissions

    await update.effective_chat.send_message("⏳ Logging in...")

    result = await telegram_login(email, password, chat_id, username)
    if result:
        context.user_data["linked_user"] = result
        context.user_data.pop("login_email", None)
        await update.effective_chat.send_message(
            f"✅ <b>Login Successful!</b>\n\n"
            f"👤 Name: {result.get('name', 'N/A')}\n"
            f"📧 Email: {result.get('email', 'N/A')}\n\n"
            f"You can now upload invoices! Use the menu below.",
            parse_mode="HTML",
            reply_markup=_main_menu_kb(),
        )
        return MAIN_MENU
    else:
        await update.effective_chat.send_message(
            "❌ <b>Invalid email or password.</b>\n\n"
            "Please try again.\n\n"
            "📧 <b>Enter your email address:</b>",
            parse_mode="HTML",
        )
        context.user_data.pop("login_email", None)
        return WAITING_FOR_EMAIL


# ══════════════════════════════════════════════════════
#  MAIN MENU
# ══════════════════════════════════════════════════════

def _main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📄 Upload Invoice", callback_data="menu_upload")],
        [InlineKeyboardButton("📋 My Invoices", callback_data="menu_invoices")],
        [InlineKeyboardButton("ℹ️ Account Status", callback_data="menu_status")],
    ])


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /menu command."""
    chat_id = str(update.effective_chat.id)
    user_data = await check_user_linked(chat_id)
    if not user_data:
        await update.message.reply_text(
            "⚠️ You need to link your account first. Send /start",
        )
        return ConversationHandler.END

    context.user_data["linked_user"] = user_data
    await update.message.reply_text(
        "📱 <b>InvoX Menu</b>\n\nWhat would you like to do?",
        parse_mode="HTML",
        reply_markup=_main_menu_kb(),
    )
    return MAIN_MENU


async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    choice = q.data
    chat_id = str(q.from_user.id)

    if choice == "menu_upload":
        await q.edit_message_text(
            "📄 <b>Upload Invoice</b>\n\n"
            "Send me your invoice as a <b>photo</b> or <b>PDF</b>.\n"
            "I'll OCR it and add it to your InvoX account.\n\n"
            "Type /cancel to go back.",
            parse_mode="HTML",
        )
        return UPLOAD_INVOICE

    elif choice == "menu_invoices":
        invoices = await get_user_invoices(chat_id)
        if not invoices:
            await q.edit_message_text(
                "📭 <b>No invoices found.</b>\n\n"
                "Upload your first invoice using the menu!",
                parse_mode="HTML",
                reply_markup=_main_menu_kb(),
            )
            return MAIN_MENU

        lines = ["📋 <b>Your Recent Invoices</b>\n"]
        emoji_map = {"draft": "📝", "issued": "📤", "paid": "✅", "overdue": "⚠️"}
        for inv in invoices[:5]:
            e = emoji_map.get(inv.get("invoice_status", ""), "📄")
            t = inv.get("grand_total", 0)
            ocr = inv.get("ocr_status", "")
            ocr_badge = ""
            if ocr == "processing":
                ocr_badge = " ⏳"
            elif ocr == "ocr_done":
                ocr_badge = " ✅"
            elif ocr == "failed":
                ocr_badge = " ❌"
            lines.append(
                f"{e} <b>#{inv['invoice_number']}</b> — ₹{t:,.0f} "
                f"[{inv['invoice_status'].upper()}]{ocr_badge}"
            )

        await q.edit_message_text(
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back to Menu", callback_data="menu_back")],
            ]),
        )
        return MAIN_MENU

    elif choice == "menu_status":
        user_data = await check_user_linked(chat_id)
        if user_data:
            await q.edit_message_text(
                f"✅ <b>Account Linked</b>\n\n"
                f"👤 Name: {user_data.get('name')}\n"
                f"📧 Email: {user_data.get('email')}\n"
                f"🎭 Role: {user_data.get('role', 'vendor').capitalize()}\n"
                f"🏢 Vendor ID: {user_data.get('vendor_id', 'N/A')}",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("◀️ Back to Menu", callback_data="menu_back")],
                ]),
            )
        else:
            await q.edit_message_text(
                "⚠️ Account not linked. Send /start to link.",
                reply_markup=_main_menu_kb(),
            )
        return MAIN_MENU

    elif choice == "menu_back":
        await q.edit_message_text(
            "📱 <b>InvoX Menu</b>\n\nWhat would you like to do?",
            parse_mode="HTML",
            reply_markup=_main_menu_kb(),
        )
        return MAIN_MENU

    return MAIN_MENU


# ══════════════════════════════════════════════════════
#  INVOICE UPLOAD
# ══════════════════════════════════════════════════════

async def upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document or photo upload."""
    msg = update.message
    chat_id = str(update.effective_chat.id)

    # Check if authenticated
    user_data = await check_user_linked(chat_id)
    if not user_data:
        await msg.reply_text(
            "⚠️ You need to link your account first.\n"
            "Send /start to begin.",
        )
        return ConversationHandler.END

    # Get file
    file_obj = None
    file_name = "invoice.jpg"

    if msg.document:
        file_obj = msg.document
        file_name = msg.document.file_name or "invoice.pdf"
    elif msg.photo:
        file_obj = msg.photo[-1]  # highest resolution
        file_name = f"invoice_{chat_id}.jpg"
    else:
        await msg.reply_text(
            "⚠️ Please send a <b>photo</b> or a <b>PDF/image file</b>.",
            parse_mode="HTML",
        )
        return UPLOAD_INVOICE

    await msg.reply_text("⏳ Uploading invoice to InvoX...")

    try:
        tg_file = await file_obj.get_file()
        file_bytes = await tg_file.download_as_bytearray()

        code, data = await upload_invoice_file(chat_id, file_name, bytes(file_bytes))

        if code == 200:
            inv_id = data.get("invoice_id", "?")
            await msg.reply_text(
                f"✅ <b>Invoice uploaded!</b>\n\n"
                f"📁 File: <code>{file_name}</code>\n"
                f"🔄 OCR processing started...\n\n"
                f"You'll get a notification when OCR completes.\n"
                f"Use /menu to continue.",
                parse_mode="HTML",
                reply_markup=_main_menu_kb(),
            )
        else:
            detail = data.get("detail", "Unknown error")
            await msg.reply_text(
                f"❌ Upload failed: {detail}\n\nTry again or /cancel.",
            )
            return UPLOAD_INVOICE
    except Exception as e:
        logger.error(f"Upload error: {e}")
        await msg.reply_text("❌ Error uploading. Please try again.")
        return UPLOAD_INVOICE

    return MAIN_MENU


# ══════════════════════════════════════════════════════
#  STANDALONE COMMANDS
# ══════════════════════════════════════════════════════

async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_data = await check_user_linked(chat_id)
    if user_data:
        await update.message.reply_text(
            f"✅ <b>Account Linked</b>\n\n"
            f"👤 {user_data.get('name')}\n"
            f"📧 {user_data.get('email')}\n"
            f"🏢 Vendor ID: {user_data.get('vendor_id', 'N/A')}",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(
            "⚠️ No account linked. Send /start to link.",
        )


async def invoices_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    invoices = await get_user_invoices(chat_id)
    if not invoices:
        await update.message.reply_text("📭 No invoices found.")
        return
    lines = ["📋 <b>Recent Invoices</b>\n"]
    for inv in invoices[:5]:
        lines.append(
            f"• <b>#{inv['invoice_number']}</b> — ₹{inv['grand_total']:,.0f} "
            f"[{inv['invoice_status'].upper()}]"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="HTML")


async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /upload command."""
    chat_id = str(update.effective_chat.id)
    user_data = await check_user_linked(chat_id)
    if not user_data:
        await update.message.reply_text("⚠️ Link your account first. Send /start")
        return ConversationHandler.END

    await update.message.reply_text(
        "📄 <b>Upload Invoice</b>\n\n"
        "Send me your invoice as a <b>photo</b> or <b>PDF</b>.\n"
        "Type /cancel to go back.",
        parse_mode="HTML",
    )
    return UPLOAD_INVOICE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Cancelled. Type /start or /menu to begin again.",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ <b>InvoX Bot Commands</b>\n\n"
        "/start — Log in with email & password\n"
        "/upload — Upload an invoice image/PDF\n"
        "/menu — Main menu\n"
        "/status — Check linked account\n"
        "/invoices — View recent invoices\n"
        "/cancel — Cancel current flow\n"
        "/help — Show this message\n\n"
        "📄 <b>How it works:</b>\n"
        "1. Send /start and enter your InvoX email & password\n"
        "2. Once logged in, upload invoice photos or PDFs\n"
        "3. OCR extracts data automatically!",
        parse_mode="HTML",
    )


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 I didn't understand that. Type /help for commands.",
    )


# ══════════════════════════════════════════════════════
#  APP SETUP & MAIN
# ══════════════════════════════════════════════════════

def main():
    if not TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    app = ApplicationBuilder().token(TOKEN).build()

    # Main conversation handler
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("menu", menu_command),
            CommandHandler("upload", upload_command),
        ],
        states={
            WAITING_FOR_EMAIL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_email),
            ],
            WAITING_FOR_PASSWORD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_password),
            ],
            MAIN_MENU: [
                CallbackQueryHandler(menu_callback),
            ],
            UPLOAD_INVOICE: [
                MessageHandler(filters.Document.ALL | filters.PHOTO, upload_handler),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
        per_chat=True,
    )

    app.add_handler(conv)

    # Standalone commands (outside conversation)
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("invoices", invoices_cmd))
    app.add_handler(CommandHandler("help", help_command))

    # Document/photo handler (outside conversation — auto upload for authenticated users)
    app.add_handler(MessageHandler(filters.Document.ALL | filters.PHOTO, upload_handler))

    # Unknown text fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown))

    logger.info(f"🤖 InvoX Bot starting — connected to {BACKEND_URL}")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()


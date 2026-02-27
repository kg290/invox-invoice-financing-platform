# InvoX Telegram Bot — Standalone Integration Package

Complete Telegram bot for MSME invoice management. Includes bot script, backend API routes, notification service, and Google Cloud Vision OCR service.

## 📁 Folder Structure

```
telegram-bot-package/
├── .env.example                    # Environment variables template
├── README.md                       # This file
│
├── bot/                            # 🤖 Telegram Bot (python-telegram-bot)
│   ├── invox_bot.py                # Main bot script (1100+ lines)
│   ├── requirements.txt            # Bot Python deps
│   └── user_map.json               # Local user cache (auto-managed)
│
├── backend-routes/                 # 🔌 FastAPI routes to add to your backend
│   ├── telegram.py                 # /api/telegram/* endpoints (webhook, upload, link, etc.)
│   └── auth.py                     # /api/auth/* endpoints (includes telegram-login)
│
├── backend-services/               # ⚙️ Backend helper services
│   └── telegram_service.py         # Send messages via Bot API (OTP, notifications)
│
└── ocr-service/                    # 🔍 OCR Microservice (Google Cloud Vision)
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                 # FastAPI app (port 8001)
    │   ├── extractor.py            # Google Vision OCR + field extraction
    │   ├── preprocessor.py         # Image preprocessing (grayscale, deskew, binarize)
    │   ├── patterns.py             # Regex patterns for Indian invoices
    │   ├── invoice_client.py       # HTTP client to callback main backend
    │   ├── events.py               # Redis pub/sub (optional)
    │   └── subscriber.py           # Redis subscriber (optional)
    ├── kg-hackathon-b81a207e09b0.json  # Google Cloud Vision service account key
    ├── requirements.txt            # OCR service Python deps
    └── Dockerfile                  # Docker build for OCR service
```

## 🚀 Quick Start

### 1. Bot Setup

```bash
cd bot/
pip install -r requirements.txt
```

Create `.env` in the `bot/` folder (or set environment variables):

```env
TELEGRAM_BOT_TOKEN=<your_bot_token_from_BotFather>
BACKEND_URL=http://localhost:8000
```

Start the bot:
```bash
python invox_bot.py
```

### 2. Backend Integration

Copy these files into your FastAPI backend:

| Source File | Copy To |
|-------------|---------|
| `backend-routes/telegram.py` | `your_backend/routes/telegram.py` |
| `backend-routes/auth.py` | `your_backend/routes/auth.py` |
| `backend-services/telegram_service.py` | `your_backend/services/telegram_service.py` |

Then register the router in your `main.py`:
```python
from routes.telegram import router as telegram_router
app.include_router(telegram_router)
```

**Required models:** The routes expect these SQLAlchemy models:
- `User` — with `telegram_chat_id`, `telegram_username`, `vendor_id` columns
- `Vendor` — vendor profile
- `Invoice` — with `ocr_status`, `ocr_confidence`, `file_path` columns
- `Notification` — for system notifications

### 3. OCR Service Setup

```bash
cd ocr-service/
pip install -r requirements.txt
python -m app.main
```

Runs on port **8001**. Uses the Google Cloud Vision API key automatically.

## 🤖 Bot Features

| Feature | Description |
|---------|-------------|
| `/start` | Welcome + **Create Account** or **Login with Existing** |
| Login flow | Email + password authentication via backend API |
| Onboarding | Full MSME profile: business name, GSTIN, PAN, bank, industry |
| Invoice upload | Upload PDF/image → auto-trigger OCR extraction |
| Manual entry | Step-by-step invoice creation with GST calculation |
| `/invoices` | View recent invoices with amounts and statuses |
| `/menu` | Main menu with inline keyboard buttons |
| Instant login | Use Chat ID on the web app login page |

## 🔑 API Endpoints (Backend)

### Telegram Routes (`/api/telegram/`)

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/webhook` | None | Telegram webhook handler |
| POST | `/link` | JWT | Generate link token |
| POST | `/confirm-link` | None | Bot confirms account link |
| POST | `/link-by-email` | None | Link chat_id to user by email |
| GET | `/status-by-chat/{chat_id}` | None | Look up user by chat_id |
| GET | `/invoices-by-chat/{chat_id}` | None | Get invoices by chat_id |
| POST | `/upload` | None | File upload from bot |
| POST | `/create-vendor` | None | Create vendor during onboarding |

### Auth Routes (`/api/auth/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/telegram-login` | Instant login via chat_id (no OTP) |

### OCR Routes (`/api/invoices/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| PATCH | `/{id}/ocr-result` | Receive OCR extraction results |
| POST | `/{id}/trigger-ocr` | Trigger OCR on an invoice file |

## 🌐 Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | — | Bot token from @BotFather |
| `BACKEND_URL` | `http://localhost:8000` | Main backend API URL |
| `TELEGRAM_BOT_USERNAME` | `InvoXBot` | Bot username (without @) |
| `OCR_SERVICE_URL` | `http://localhost:8001` | OCR microservice URL |
| `UPLOAD_DIR` | `uploads` | File upload directory |
| `GOOGLE_APPLICATION_CREDENTIALS` | auto-detected | Vision API key path |

## 🏗️ Architecture

```
┌──────────────┐     ┌─────────────────┐     ┌───────────────┐
│  Telegram    │────▶│  Bot Script     │────▶│  Backend API  │
│  User Chat   │     │  (invox_bot.py) │     │  (port 8000)  │
└──────────────┘     └────────┬────────┘     └───────┬───────┘
                              │                       │
                              │ PDF upload            │ trigger
                              ▼                       ▼
                     ┌─────────────────┐     ┌───────────────┐
                     │  File Storage   │     │  OCR Service  │
                     │  (uploads/)     │     │  (port 8001)  │
                     └─────────────────┘     │  Vision API   │
                                             └───────────────┘
```

## 📋 Dependencies Summary

**Bot:** `python-telegram-bot`, `httpx`, `python-dotenv`  
**OCR:** `google-cloud-vision`, `opencv-python-headless`, `Pillow`, `pdf2image`, `httpx`, `redis`  
**Backend:** `fastapi`, `httpx`, `sqlalchemy`, `pydantic`

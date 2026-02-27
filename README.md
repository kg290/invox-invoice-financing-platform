<p align="center">
  <img src="https://img.shields.io/badge/InvoX-Invoice%20Financing-6366f1?style=for-the-badge&logoColor=white" />
  <img src="https://img.shields.io/badge/Next.js-16-black?style=for-the-badge&logo=next.js" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi" />
  <img src="https://img.shields.io/badge/Blockchain-Enabled-F7931A?style=for-the-badge&logo=bitcoin" />
  <img src="https://img.shields.io/badge/IPFS-Pinata-E4405F?style=for-the-badge" />
  <img src="https://img.shields.io/badge/Google%20Gemini-AI-4285F4?style=for-the-badge&logo=google" />
</p>

<h1 align="center">🧾 InvoX — AI-Powered Invoice Financing for Indian MSMEs</h1>

<p align="center">
  <strong>Blockchain-backed · IPFS-stored · AI-negotiated · Fractional · Instant</strong>
</p>

<p align="center">
  From invoice creation to funded in <strong>under 3 minutes</strong> — with cryptographic proof, AI negotiation, and community lending.
</p>

<p align="center">
  <a href="#-the-problem">Problem</a> •
  <a href="#-features">Features</a> •
  <a href="#-tech-stack">Tech Stack</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-getting-started">Getting Started</a> •
  <a href="#-api-reference">API Reference</a>
</p>

---

## 🎯 The Problem

**43 million Indian MSMEs** are strangled by cash-flow gaps. Buyers delay payments 60–120 days. Banks reject 80% of MSME loan applications. Traditional invoice discounting demands collateral, takes weeks, and charges opaque rates.

> A street-food vendor with a ₹50,000 hospital invoice waits 3 months to get paid. InvoX lets them get funded — **today**.

---

## 💡 Problem → Solution

| Pain Point | InvoX Solution |
|-----------|---------------|
| Long wait for invoice payment | List on marketplace, get funded in minutes |
| Opaque interest rates | AI Negotiator finds the best rate automatically |
| Risk of double-financing | Blockchain registry prevents reuse |
| No tamper-proof records | Invoices pinned to IPFS (Pinata) with SHA-256 hash |
| High barrier for small lenders | Community Pot — invest from ₹500 |
| Manual KYC & verification | 3-layer auto-verification (Doc → Entity → Behavior) |
| Missed repayment deadlines | NPCI e-Mandate auto-debit |

---

## 🚀 Features

### 🔗 Blockchain Invoice Registry
Every invoice is **cryptographically registered** on an append-only blockchain ledger:
- SHA-256 hashing with HMAC-BLAKE2b signatures per block
- Proof-of-Work consensus (adjustable difficulty)
- Merkle tree verification for tamper detection
- **Duplicate detection** — same invoice cannot be financed twice
- Downloadable **blockchain certificate** with full chain proof

### 📦 IPFS Document Storage via Pinata
Invoice PDFs, KYC documents, and smart contracts are **permanently stored on IPFS** via Pinata:
- Pinned to Pinata's dedicated gateway for guaranteed availability
- Content-addressed `ipfs://Qm...` CIDs stored alongside `pdf_hash` in DB
- Document integrity verifiable by anyone with the CID — forever
- No central server holds your documents

### 🤝 Community Pot — Fractional Invoice Financing
Multiple lenders co-fund a single invoice:
- Invest from as little as **₹500**
- Live funding progress bar with real-time investor roster
- Ownership percentages tracked per lender for pro-rata repayment splits
- Fully compatible with AI negotiator for per-slice rates

### 🤖 AI Negotiator (Google Gemini 1.5 Flash)
An autonomous AI agent negotiates interest rates **on behalf of vendors**:
- Analyzes lender bids vs. market benchmarks and credit score
- Counter-offers in real-time via natural-language chat
- Locks in agreed price with smart-contract-backed PDF
- Vendors get cheaper capital without manual negotiation

### 🛡️ Triple Verification Engine
Three independent verification layers before any invoice goes live:
- **Layer 1 — Document:** OCR field extraction, HSN code validation, GST cross-check, calculation audit
- **Layer 2 — Entity:** Live GSTIN lookup (Sandbox.co.in), PAN-GSTIN linkage, Udyam cross-check, bank penny-drop
- **Layer 3 — Behavioral:** Payment velocity analysis, circular-invoicing detection, anomaly scoring

### 📊 Real-Time ML Credit Scoring
Dynamic 0–100 scores computed from 6 weighted factors:

| Component | Weight |
|-----------|--------|
| CIBIL Score | 30% |
| GST Filing Compliance | 20% |
| Platform Repayment History | 20% |
| Bank Account Health | 15% |
| Invoice Quality Index | 10% |
| Business Stability / Age | 5% |

Outputs: Risk grade (AAA → D), AI-suggested interest rate, max fundable limit.

### 💳 InvoX Pay — Integrated Payment Gateway
Custom payment orchestration layer:
- Razorpay-compatible checkout flow
- Handles funding disbursements, repayments, and bulk pay-all
- Role-based UI — vendors see repayment CTAs, lenders see ROI tracking

### 🏦 NPCI e-Mandate Auto-Repayment
- API-based e-mandate registration with bank account linking
- Due-date triggers auto-debit with 3-day retry on failure
- Escalation workflows for persistent failures

### 📄 Invoice Factoring (3 Modes)

| Mode | Rate Range | Risk Bearer |
|------|-----------|-------------|
| **Non-Recourse** | 18–24% | Lender |
| **Partial Recourse** | 14–18% | 50/50 shared |
| **Full Recourse** | 10–14% | Vendor |

### 📝 Smart Contract PDFs
Post-negotiation settlement contracts auto-generated:
- Legally structured with agreed rate, amount, and tenure
- Blockchain hash embedded as tamper-evident seal
- IPFS CID reference for permanent storage
- Downloadable by both vendor and lender

### 🔍 Google Cloud Vision OCR
Dedicated OCR microservice:
- Handles JPEG, PNG, and PDF uploads
- Pre-processing: grayscale, deskew, binarize
- Regex patterns tuned for Indian formats (GSTIN, HSN, ₹ amounts)
- Auto-creates invoice drafts after extraction

### 📧 Gmail Invoice Ingestion
- Forward invoices to a dedicated Gmail inbox
- PDF/image attachments auto-parsed with Vision OCR
- Data pre-filled — one click to list on marketplace

### 🤖 Telegram Bot (`@InvoX_Bot`)
- `/start` — Link Telegram to InvoX via secure token
- Upload invoice photos → OCR → auto-create draft
- Real-time funding alerts, OTP codes, repayment reminders
- `/status`, `/balance`, `/invoices` quick commands

### 🏛️ Government API Integrations (Sandbox.co.in)
- Live GSTIN validity and compliance status
- PAN verification and PAN-GSTIN linkage
- IEC (Import Export Code) lookup
- Bank account penny-drop verification

---

## 🧰 Tech Stack

### Backend
| Technology | Role |
|-----------|------|
| **Python 3.12** | Runtime |
| **FastAPI** | Async REST API (70+ endpoints) |
| **SQLAlchemy + SQLite (WAL)** | ORM + database |
| **ReportLab** | GST-compliant PDF generation |
| **hashlib / cryptography** | Blockchain SHA-256, HMAC-BLAKE2b |
| **Google Gemini 1.5 Flash** | AI Negotiator agent |
| **Pinata SDK** | IPFS document pinning |
| **HTTPX** | Async HTTP for external APIs |

### Frontend
| Technology | Role |
|-----------|------|
| **Next.js 16 (App Router)** | React SSR/CSR framework |
| **TypeScript** | End-to-end type safety |
| **Tailwind CSS 4** | Utility-first styling |
| **Recharts** | Dashboard analytics |
| **React Hook Form + Zod** | Schema-validated forms |
| **Lucide React** | Icon library |

### Infrastructure & Storage
| Technology | Role |
|-----------|------|
| **IPFS + Pinata** | Decentralised document storage |
| **Docker + Compose** | Containerisation |
| **Google Cloud Run** | Serverless production deployment |
| **Vercel** | Frontend CDN |

### External APIs
| API | Purpose |
|-----|---------|
| **Pinata (IPFS)** | Permanent decentralised document storage |
| **Sandbox.co.in** | GSTIN, PAN, bank verification |
| **Google Gemini 1.5** | AI negotiation agent |
| **Google Cloud Vision** | Invoice OCR |
| **Gmail API** | Email invoice ingestion |
| **Telegram Bot API** | Mobile management |
| **NPCI e-Mandate** | Auto-repayment debit |

---

## 🏗️ Architecture

```
╔══════════════════════════════════════════════════════════════════╗
║                         FRONTEND                                 ║
║              Next.js 16 · React 19 · TypeScript                  ║
║         Tailwind CSS · Recharts · React Hook Form · Zod          ║
╚══════════════════════════════════════════╤═══════════════════════╝
                                           │ Axios REST (JWT Bearer)
                                           ▼
╔══════════════════════════════════════════════════════════════════╗
║                    FASTAPI BACKEND (70+ endpoints)               ║
║                                                                  ║
║  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌───────────────┐   ║
║  │  Auth    │ │ Invoices │ │ Marketplace  │ │ Admin/Dash    │   ║
║  │ JWT+OTP  │ │ CRUD+PDF │ │ Community Pot│ │ Analytics     │   ║
║  └──────────┘ └──────────┘ └──────────────┘ └───────────────┘   ║
║                                                                  ║
║  ┌─────────────────────────────────────────────────────────┐     ║
║  │              ADVANCED SERVICES LAYER                    │     ║
║  │  Blockchain   Triple-Verify  Credit    Factoring        │     ║
║  │  Registry     (3 layers)     Scoring   Engine           │     ║
║  │  AI Negotiator   e-Mandate   Gmail Ingestion            │     ║
║  │  Telegram Bot    OCR Service InvoX Pay Gateway          │     ║
║  └─────────────────────────────────────────────────────────┘     ║
╚══════════╤═══════════════════════════╤════════════════╤══════════╝
           │                           │                │
  ┌────────▼───────┐        ┌──────────▼──────┐  ┌─────▼──────────┐
  │  SQLite + WAL  │        │  IPFS (Pinata)  │  │ External APIs  │
  │  (SQLAlchemy)  │        │  pdf CIDs, docs │  │ Gemini·Sandbox │
  └────────────────┘        └─────────────────┘  │ Vision·Telegram│
                                                  └────────────────┘

BLOCKCHAIN LEDGER (append-only, in-process)
  Block 0 (Genesis) → Block 1 (Invoice #1) → ··· → Block N
  Each block: SHA-256 + HMAC-BLAKE2b · PoW · Merkle proof

IPFS via Pinata
  Invoice PDF ──► Pinata pin ──► ipfs://Qm...CID ──► stored in DB
```

---

## ⚡ Data Flow — Invoice to Funded

```
1.  VENDOR creates invoice  →  GST PDF built by ReportLab
2.  BLOCKCHAIN REGISTER     →  SHA-256 hash, PoW block mined
3.  IPFS PIN                →  PDF uploaded to Pinata → CID in DB
4.  TRIPLE VERIFY           →  Doc + Entity + Behavioral (parallel)
5.  MARKETPLACE LISTING     →  Community Pot opened (min ₹500)
6.  AI NEGOTIATOR           →  Lender bids → Gemini counters → lock
7.  SMART CONTRACT PDF      →  Sealed with blockchain hash + IPFS CID
8.  INVOX PAY               →  Lender funds → disbursement to vendor
9.  REPAYMENT               →  e-Mandate auto-debit → pro-rata to lenders
```

---

## 🛠️ Getting Started

### Prerequisites
- Python 3.12+, Node.js 20+, Docker (optional)

### Option A: Docker Compose

```bash
git clone https://github.com/kg290/invox-invoice-financing-platform.git
cd invox-invoice-financing-platform
docker-compose up --build
# Frontend → http://localhost:3000
# Backend  → http://localhost:8000/docs
```

### Option B: Manual

```bash
# Backend
cd backend
python -m venv venv && .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
# copy .env.example to .env and fill in your keys
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > .env.local
npm run dev
```

### Seed Demo Data

```bash
curl -X POST http://localhost:8000/api/seed/demo
curl -X POST http://localhost:8000/api/seed/demo-users
```

| Role | Email | Password |
|------|-------|----------|
| Vendor | vendor@invox.demo | Demo@1234 |
| Lender | lender@invox.demo | Demo@1234 |
| Admin | admin@invox.demo | Demo@1234 |

---

## 📡 API Reference

Base URL: `http://localhost:8000/api` · Swagger UI: **`/docs`**

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register vendor / lender |
| POST | `/auth/verify-otp` | Verify OTP, activate account |
| POST | `/auth/login` | Login → JWT token |

### Invoices
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/invoices/` | Create GST-compliant invoice |
| GET | `/invoices/vendor/{id}` | List vendor invoices |
| GET | `/invoices/{id}/pdf` | Download PDF |

### Marketplace
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/marketplace/` | Browse listings |
| POST | `/marketplace/list/{invoice_id}` | List for Community Pot |
| GET | `/marketplace/listings/{id}` | Detail + investors |
| GET | `/marketplace/listings/{id}/repayment` | Repayment schedule |

### Blockchain & IPFS
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/blockchain-registry/register/{invoice_id}` | Mine block + Pinata pin |
| GET | `/blockchain-registry/verify/{invoice_id}` | Cryptographic check |
| GET | `/blockchain-registry/certificate/{invoice_id}` | Tamper-proof certificate |
| GET | `/blockchain-registry/chain` | Full ledger |

### AI Negotiator
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/negotiate/{listing_id}/start` | Start negotiation session |
| POST | `/negotiate/{session_id}/message` | Send message to AI |
| POST | `/negotiate/{session_id}/lock-price` | Lock agreed price |

### Credit Scoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/credit-score/vendor/{id}` | 0–100 score |
| GET | `/credit-score/breakdown/{id}` | 6-component breakdown |
| GET | `/credit-score/recommended-rate/{id}` | AI-suggested rate |

### Factoring / e-Mandate / KYC
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/factoring/options/{listing_id}` | All recourse mode rates |
| POST | `/emandate/register` | Register NPCI e-mandate |
| POST | `/govt/gstin/{gstin}` | Live GSTIN check |
| POST | `/govt/pan/{pan}` | PAN verification |

---

## 📁 Project Structure

```
invox-invoice-financing-platform/
├── backend/
│   ├── main.py                     # FastAPI app + router mounting
│   ├── models.py                   # SQLAlchemy models (20+ tables)
│   ├── blockchain.py               # PoW ledger (SHA-256 + HMAC-BLAKE2b)
│   ├── pdf_generator.py            # ReportLab GST invoice PDFs
│   ├── smart_contract_pdf.py       # Settlement contract PDFs
│   ├── routes/                     # 18 route modules
│   └── services/                   # Business logic services
│       ├── blockchain_registry.py  # Blockchain + Pinata IPFS
│       ├── ai_negotiator.py        # Gemini agent (700+ lines)
│       ├── credit_scoring.py       # ML scoring algorithms
│       ├── triple_verification.py  # 3-layer verification
│       ├── emandate.py             # NPCI mandate orchestration
│       └── ...
├── frontend/
│   └── src/app/
│       ├── vendor/[id]/            # Vendor dashboard, invoices, negotiations
│       ├── lender/                 # Lender dashboard + ROI
│       ├── marketplace/            # Browse + Community Pot detail
│       └── admin/                  # Admin dashboard
├── Gmail integration/              # Email invoice ingestion
├── telegram-bot-package/
│   ├── bot/invox_bot.py            # Telegram bot (1100+ lines)
│   └── ocr-service/                # Google Vision OCR microservice
├── docker-compose.yml
├── deploy-gcp.sh / .ps1
└── start.ps1 / run_bot.ps1
```

---

## 🔐 Security

- JWT tokens with 24h expiry
- OTP on registration and sensitive actions
- Blockchain integrity — tamper-evident chain proof per invoice
- IPFS content addressing — a changed doc has a different CID
- Duplicate financing prevention
- Role-based access control (vendor / lender / admin)
- All secrets in `.env` — never committed

---

## 🌐 Deployment

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `JWT_SECRET` | ✅ | JWT signing secret |
| `BLOCK_SIGNING_KEY` | ✅ | Blockchain HMAC key |
| `INVOX_PAY_SECRET` | ✅ | Payment gateway secret |
| `GEMINI_API_KEY` | Optional | Google Gemini (AI Negotiator) |
| `PINATA_API_KEY` | Optional | Pinata IPFS API key |
| `PINATA_SECRET_KEY` | Optional | Pinata IPFS secret |
| `Sandbox_API_KEYNAME` | Optional | Sandbox.co.in key |
| `TELEGRAM_BOT_TOKEN` | Optional | Telegram bot token |
| `GOOGLE_APPLICATION_CREDENTIALS` | Optional | GCP Vision service account |

---

## 📊 Platform Stats (Demo Data)

| Metric | Value |
|--------|-------|
| Invoices Created | 1,240+ |
| Total Volume Financed | ₹2.4 Cr+ |
| Average Funding Time | 4.2 minutes |
| AI Negotiations Completed | 380+ |
| Blockchain Blocks Mined | 1,240+ |
| Documents on IPFS | 1,240+ |
| Active Lenders | 56 |
| MSME Vendors Onboarded | 210+ |
| Avg. Interest Rate Achieved | 13.8% |
| Repayment Success Rate | 94.2% |

---

## 🏆 Why InvoX

1. **End-to-end automation** — invoice → blockchain → IPFS → verify → list → AI negotiate → fund → auto-repay
2. **True decentralisation** — documents on IPFS, not just a cloud server
3. **Community Pot** — democratises lending; anyone with ₹500 can participate
4. **AI-first** — Gemini agent negotiates 24/7 on behalf of vendors
5. **India-native** — GSTIN, HSN, NPCI e-Mandate, Udyam, Sandbox.co.in
6. **Production-ready** — Docker + GCP Cloud Run + CI/CD + WAL SQLite

---

<p align="center">
  Built with ❤️ for Indian MSMEs by the <strong>InvoX Team</strong><br/>
  <em>InnovateYou Hackathon 2026</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Made%20in-India-FF9933?style=flat-square" />
  <img src="https://img.shields.io/badge/For-MSMEs-138808?style=flat-square" />
  <img src="https://img.shields.io/badge/Powered%20by-Blockchain%20%2B%20AI-6366f1?style=flat-square" />
</p>


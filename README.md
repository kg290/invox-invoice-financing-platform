<p align="center">
  <h1 align="center">InvoX — Invoice Financing Platform for MSMEs</h1>
  <p align="center">
    <strong>AI-Powered, Blockchain-Backed Invoice Financing & Marketplace</strong>
  </p>
  <p align="center">
    <a href="#features">Features</a> •
    <a href="#tech-stack">Tech Stack</a> •
    <a href="#architecture">Architecture</a> •
    <a href="#getting-started">Getting Started</a> •
    <a href="#api-reference">API Reference</a> •
    <a href="#deployment">Deployment</a>
  </p>
</p>

---

## Overview

**InvoX** is a full-stack embedded invoice financing platform designed for Indian MSMEs (Micro, Small & Medium Enterprises). It connects vendors who need working capital with lenders willing to fund verified invoices — all powered by AI negotiation, blockchain-backed verification, and real-time credit scoring.

### The Problem
MSMEs wait **60–120 days** for invoice payments, leading to severe cash-flow crunch. Traditional invoice discounting requires manual paperwork, offers opaque rates, and has high entry barriers for small lenders.

### The Solution
InvoX digitizes the entire invoice lifecycle — from creation and GST verification through marketplace listing, AI-negotiated funding, and auto-repayment via NPCI e-Mandate — reducing financing time from **weeks to minutes**.

---

## Features

### Core Platform
| Feature | Description |
|---------|-------------|
| **JWT + OTP Authentication** | Secure login with email/phone OTP verification |
| **Vendor Onboarding & KYC** | PAN, Aadhaar, GSTIN verification via Sandbox.co.in APIs |
| **GST-Compliant Invoicing** | Create invoices with HSN codes, auto-calculated GST, and PDF generation |
| **Invoice Marketplace** | Lenders browse and fund verified invoices at competitive rates |
| **Repayment Schedules** | EMI-based repayment tracking with automated reminders |
| **Admin Dashboard** | Platform-wide analytics, user management, and system oversight |
| **InvoX Pay Gateway** | Integrated payment processing for disbursements and repayments |

### Advanced Features

#### 🔗 Blockchain Invoice Registry
Every invoice is registered on an immutable blockchain ledger with SHA-256 hashing, HMAC signatures, and Merkle tree proofs. Duplicate detection prevents double-financing, and cryptographic certificates provide legal standing in Indian courts.

#### 🛡️ Triple Verification Engine
Three-layer verification system:
- **Layer 1 — Document:** OCR extraction, GST portal cross-match, HSN validation, calculation checks
- **Layer 2 — Entity:** Live GSTIN verification, PAN-GSTIN linkage, bank penny-drop simulation, Udyam cross-check
- **Layer 3 — Behavioral:** Payment history analysis, pattern detection (circular invoicing, duplicates), velocity checks, amount anomaly detection

#### 📊 Real-Time ML Credit Scoring
Dynamic credit scores (0–100) computed from 6 weighted components: CIBIL score, GST compliance, platform repayment history, bank account health, invoice quality, and business stability. Outputs risk grades (AAA→D), recommended interest rates, and max funding limits.

#### 📄 Invoice Factoring with Recourse Options
Three factoring modes for different risk appetites:
- **Non-Recourse** (18–24%) — Lender absorbs all default risk
- **Partial Recourse** (14–18%) — 50/50 risk sharing between vendor and lender
- **Full Recourse** (10–14%) — Vendor guarantees repayment; lowest rates

#### 🏦 NPCI e-Mandate Auto-Repayment
Vendors register NPCI e-Mandates for recurring auto-debit. On due dates the system triggers bank debits automatically, with 3-day retry logic and escalation workflows for failures.

#### 🤖 AI Negotiator Agent
Powered by Google Gemini, an autonomous AI agent negotiates interest rates on behalf of vendors. It analyzes lender bids against market data, credit scores, and historical rates to counter-offer for optimal terms — achieving cheaper capital without manual intervention.

#### 📧 Gmail Integration
Forward invoices via email for automatic extraction and processing. PDF attachments are parsed, invoice data is extracted, and financing can be triggered with zero manual upload.

---

## Tech Stack

### Backend
| Technology | Purpose |
|-----------|---------|
| **Python 3.12** | Runtime |
| **FastAPI** | Async REST API framework |
| **SQLAlchemy** | ORM & database models |
| **SQLite** | Lightweight database (production-ready with WAL mode) |
| **Uvicorn** | ASGI server |
| **ReportLab** | PDF invoice generation |
| **Cryptography** | Blockchain hashing, JWT signing |
| **HTTPX** | Async HTTP client for external API calls |
| **Google Gemini** | AI negotiation agent |

### Frontend
| Technology | Purpose |
|-----------|---------|
| **Next.js 16** | React framework with App Router |
| **React 19** | UI library |
| **TypeScript** | Type safety |
| **Tailwind CSS 4** | Utility-first styling |
| **Recharts** | Dashboard charts & analytics |
| **React Hook Form + Zod** | Form validation |
| **Axios** | HTTP client |
| **Lucide React** | Icon library |
| **Sonner** | Toast notifications |

### Infrastructure
| Technology | Purpose |
|-----------|---------|
| **Docker** | Containerization (multi-stage builds) |
| **Docker Compose** | Local orchestration |
| **Google Cloud Run** | Production deployment |
| **Vercel** | Frontend hosting (optional) |

### External APIs
| API | Purpose |
|-----|---------|
| **Sandbox.co.in** | Live GSTIN verification, GST compliance checks |
| **Google Gemini** | AI-powered negotiation agent |
| **Gmail API** | Email invoice ingestion |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│                   Next.js 16 + React 19                      │
│              (Tailwind CSS, Recharts, Zod)                   │
└──────────────────────┬───────────────────────────────────────┘
                       │ REST API (Axios)
                       ▼
┌──────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                         │
│                                                              │
│  ┌─────────┐ ┌──────────┐ ┌───────────┐ ┌───────────────┐   │
│  │  Auth   │ │ Invoices │ │Marketplace│ │  Admin/Dash   │   │
│  │ (JWT+   │ │ (CRUD +  │ │ (Listings │ │  (Analytics)  │   │
│  │  OTP)   │ │  PDF)    │ │ + Bids)   │ │               │   │
│  └─────────┘ └──────────┘ └───────────┘ └───────────────┘   │
│                                                              │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │              ADVANCED SERVICES LAYER                     │ │
│  │                                                         │ │
│  │  Blockchain    Triple        Credit     Factoring       │ │
│  │  Registry      Verification  Scoring    Engine          │ │
│  │                                                         │ │
│  │  e-Mandate     AI Negotiator   Gmail Integration        │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │   SQLite DB   │  │  Blockchain  │  │  External APIs   │   │
│  │  (SQLAlchemy) │  │   Ledger     │  │ (Sandbox, Gemini)│   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

---

## Getting Started

### Prerequisites
- **Python 3.12+**
- **Node.js 20+**
- **npm** or **yarn**
- **Docker & Docker Compose** (optional, for containerized setup)

### Option A: Docker Compose (Recommended)

```bash
# Clone the repository
git clone https://github.com/kg290/invox-invoice-financing-platform.git
cd invox-invoice-financing-platform

# Start all services
docker-compose up --build

# Access:
#   Frontend → http://localhost:3000
#   Backend  → http://localhost:8000
#   API Docs → http://localhost:8000/docs
```

### Option B: Manual Setup

#### Backend
```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\Activate.ps1
# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cat > .env << EOF
JWT_SECRET=invox-secret-key-change-in-production
FRONTEND_URL=http://localhost:3000
INVOX_PAY_SECRET=invox_pay_secret_k4x9m2p7q1w8e5
BLOCK_SIGNING_KEY=invox_chain_sign_k9x2m7p4q1w8e5r3
ENCRYPTION_KEY=invox_encrypt_a5b3c8d2e7f1g4h6
EOF

# Run the server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend
```bash
cd frontend

# Install dependencies
npm install

# Create .env.local
echo "NEXT_PUBLIC_API_URL=http://localhost:8000/api" > .env.local

# Run development server
npm run dev
```

### Demo Data
Once both servers are running, click the **"Load Demo Data"** button on the homepage or call:
```bash
curl -X POST http://localhost:8000/api/seed/demo
curl -X POST http://localhost:8000/api/seed/demo-users
```

**Demo accounts:**
| Role | Email | Password |
|------|-------|----------|
| Vendor | vendor@invox.demo | Demo@1234 |
| Lender | lender@invox.demo | Demo@1234 |
| Admin | admin@invox.demo | Demo@1234 |

---

## API Reference

Base URL: `http://localhost:8000/api`

Interactive docs available at **http://localhost:8000/docs** (Swagger UI).

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register new user (vendor/lender) |
| POST | `/auth/verify-otp` | Verify OTP and activate account |
| POST | `/auth/login` | Login and receive JWT token |

### Vendors
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/vendors/` | List all vendors |
| GET | `/vendors/{id}` | Get vendor details |
| POST | `/vendors/quick-register` | Quick vendor registration with auto GST lookup |

### Invoices
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/invoices/` | Create new invoice |
| GET | `/invoices/vendor/{vendor_id}` | List vendor's invoices |
| GET | `/invoices/{id}/pdf` | Download invoice PDF |

### Marketplace
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/marketplace/` | Browse available listings |
| POST | `/marketplace/list` | List invoice for financing |
| POST | `/marketplace/{id}/fund` | Fund a listing |

### Blockchain Registry
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/blockchain-registry/register/{invoice_id}` | Register invoice on blockchain |
| GET | `/blockchain-registry/verify/{invoice_id}` | Verify invoice integrity |
| GET | `/blockchain-registry/certificate/{invoice_id}` | Download tamper-proof certificate |

### Triple Verification
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/triple-verify/invoice/{invoice_id}` | Run full 3-layer verification |
| GET | `/triple-verify/report/{invoice_id}` | Get verification report |
| POST | `/triple-verify/gstin-live/{gstin}` | Live GSTIN verification |

### Credit Scoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/credit-score/vendor/{vendor_id}` | Get real-time credit score |
| GET | `/credit-score/breakdown/{vendor_id}` | Detailed score breakdown |
| GET | `/credit-score/recommended-rate/{vendor_id}` | AI-suggested interest rate |

### Factoring
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/factoring/options/{listing_id}` | Calculate rates for all recourse types |
| POST | `/factoring/create` | Create factoring agreement |

### e-Mandate
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/emandate/register` | Register new e-mandate |
| POST | `/emandate/execute` | Execute auto-debit |
| POST | `/emandate/retry-failed` | Batch retry failed debits |

### AI Negotiator
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ai-negotiator/negotiate` | Start AI-powered rate negotiation |

---

## Project Structure

```
├── backend/
│   ├── main.py                  # FastAPI app entrypoint
│   ├── models.py                # SQLAlchemy database models
│   ├── database.py              # DB engine & session config
│   ├── schemas.py               # Pydantic request/response schemas
│   ├── pdf_generator.py         # Invoice PDF generation (ReportLab)
│   ├── blockchain.py            # Core blockchain ledger (PoW + signatures)
│   ├── verification.py          # KYC verification logic
│   ├── routes/
│   │   ├── auth.py              # Authentication (register, login, OTP)
│   │   ├── vendor.py            # Vendor CRUD & quick-register
│   │   ├── invoice.py           # Invoice management
│   │   ├── marketplace.py       # Marketplace listings & funding
│   │   ├── blockchain_registry.py  # Blockchain invoice registration
│   │   ├── triple_verification.py  # 3-layer verification engine
│   │   ├── credit_scoring.py    # ML credit scoring endpoints
│   │   ├── factoring.py         # Factoring agreements & recourse
│   │   ├── emandate.py          # NPCI e-mandate management
│   │   ├── ai_negotiator.py     # AI negotiation agent
│   │   ├── admin.py             # Admin dashboard & management
│   │   ├── dashboard.py         # Analytics dashboards
│   │   ├── payment.py           # InvoX Pay gateway
│   │   └── ...
│   └── services/
│       ├── blockchain_registry.py  # Blockchain registry service
│       ├── triple_verification.py  # Verification service logic
│       ├── credit_scoring.py    # Scoring algorithms
│       ├── factoring.py         # Factoring calculations
│       ├── emandate.py          # e-Mandate orchestration
│       ├── ai_negotiator.py     # Gemini AI agent
│       ├── email_service.py     # Email notifications
│       └── govt_verification.py # Government API integrations
├── frontend/
│   └── src/
│       ├── app/
│       │   ├── page.tsx         # Landing page
│       │   ├── login/           # Login page
│       │   ├── register/        # Registration flow
│       │   ├── vendor/          # Vendor dashboard & management
│       │   ├── lender/          # Lender dashboard
│       │   ├── marketplace/     # Invoice marketplace
│       │   ├── admin/           # Admin dashboard
│       │   └── kyc/             # KYC verification page
│       ├── components/          # Shared React components
│       └── lib/
│           ├── api.ts           # Axios HTTP client
│           ├── auth.tsx         # Auth context & hooks
│           ├── types.ts         # TypeScript interfaces
│           └── validation.ts    # Zod schemas
├── Gmail integration/           # Email-based invoice ingestion
├── docker-compose.yml           # Full-stack orchestration
├── deploy-gcp.sh               # Google Cloud Run deployment
└── deploy-gcp.ps1              # GCP deployment (PowerShell)
```

---

## Deployment

### Google Cloud Run

```bash
# Using the provided deployment script
chmod +x deploy-gcp.sh
./deploy-gcp.sh

# Or on Windows
.\deploy-gcp.ps1
```

### Docker

```bash
# Build individual images
docker build -t invox-backend ./backend
docker build -t invox-frontend ./frontend

# Run with compose
docker-compose up -d
```

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `JWT_SECRET` | Secret key for JWT token signing | Yes |
| `FRONTEND_URL` | Frontend URL for CORS | Yes |
| `INVOX_PAY_SECRET` | InvoX Pay gateway secret | Yes |
| `BLOCK_SIGNING_KEY` | Blockchain signing key | Yes |
| `ENCRYPTION_KEY` | Data encryption key | Yes |
| `GEMINI_API_KEY` | Google Gemini API key (for AI Negotiator) | Optional |
| `Sandbox_API_KEYNAME` | Sandbox.co.in API key name | Optional |
| `Sandbox_API_KEYNAME_SECRET` | Sandbox.co.in API secret | Optional |

---

## License

This project was built for the **InnovateYou Hackathon**.

---

<p align="center">
  Built with ❤️ by the InvoX Team
</p>

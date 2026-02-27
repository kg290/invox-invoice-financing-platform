# InvoX — Major Features Implementation Tracker
## FT004: Invoice Financing for MSMEs

---

## FEATURE 1: BLOCKCHAIN INVOICE REGISTRY (Immutable Truth)
**Status:** ✅ IMPLEMENTED
**Files:** `services/blockchain_registry.py`, `routes/blockchain_registry.py`

### What it does:
- Every invoice gets registered on blockchain with tamper-proof hash
- Buyer's GSTIN is cross-verified before registration
- Invoice hash includes: vendor signature, buyer ID, GSTN reference, timestamp
- Duplicate invoice detection (same invoice_number + buyer_gstin = REJECTED)
- Integrity verification endpoint to prove invoice was never tampered
- Cryptographic proof (SHA-256 + HMAC signature + Merkle tree)
- Legal standing: blockchain evidence accepted in Indian courts post-2020

### Endpoints:
- `POST /api/blockchain-registry/register/{invoice_id}` — Register invoice on blockchain
- `GET /api/blockchain-registry/verify/{invoice_id}` — Verify invoice integrity
- `GET /api/blockchain-registry/certificate/{invoice_id}` — Download tamper-proof certificate
- `GET /api/blockchain-registry/history/{invoice_id}` — Full audit trail
- `GET /api/blockchain-registry/stats` — Registry health & statistics

---

## FEATURE 2: TRIPLE VERIFICATION ENGINE
**Status:** ✅ IMPLEMENTED
**Files:** `services/triple_verification.py`, `routes/triple_verification.py`

### What it does:
**LAYER 1 — DOCUMENT VERIFICATION:**
- OCR-simulated invoice data extraction
- Cross-match with GST portal (Sandbox.co.in API)
- Verify invoice number uniqueness across platform
- Validate GSTIN format, state codes, HSN codes
- Auto-validate calculations (GST, totals, rounding)

**LAYER 2 — ENTITY VERIFICATION:**
- Vendor GSTIN active check (live Sandbox.co.in GST API)
- Buyer GSTIN active check (live Sandbox.co.in GST API)
- PAN-GSTIN linkage validation
- Bank account penny-drop simulation
- Udyam registration cross-check

**LAYER 3 — BEHAVIORAL VERIFICATION:**
- Buyer's past payment history on platform
- Vendor's repayment track record
- Invoice pattern analysis (duplicate detection, circular invoicing)
- Amount anomaly detection (statistical outlier check)
- Velocity check (too many invoices too fast = suspicious)

### Endpoints:
- `POST /api/triple-verify/invoice/{invoice_id}` — Run full 3-layer verification
- `GET /api/triple-verify/report/{invoice_id}` — Get verification report
- `POST /api/triple-verify/gstin-live/{gstin}` — Live GSTIN verification via Sandbox.co.in

---

## FEATURE 3: REAL-TIME CREDIT SCORING ENGINE (ML-Based)
**Status:** ✅ IMPLEMENTED
**Files:** `services/credit_scoring.py`, `routes/credit_scoring.py`

### What it does:
- Dynamic credit score computed from live data (not static CIBIL)
- Updates on every transaction, filing, or repayment

### Scoring Components (weighted):
| Component | Weight | Data Source |
|-----------|--------|-------------|
| CIBIL Score | 25% | TransUnion CIBIL |
| GST Compliance | 20% | GST Portal / Sandbox.co.in API |
| Platform Repayment History | 20% | InvoX transaction data |
| Bank Account Health | 15% | Account Aggregator simulation |
| Invoice Quality | 10% | Invoice pattern analysis |
| Business Stability | 10% | Business age + employee count + turnover trend |

### Output:
- Score: 0–100 (higher = better)
- Risk Grade: AAA / AA / A / BBB / BB / B / C / D
- Recommended Interest Rate: Auto-calculated
- Recommended Max Funding: Based on score
- Confidence Level: How reliable is this score
- Breakdown: Individual component scores

### Endpoints:
- `GET /api/credit-score/vendor/{vendor_id}` — Get real-time credit score (cached or fresh)
- `GET /api/credit-score/breakdown/{vendor_id}` — Detailed score breakdown with all 6 components
- `GET /api/credit-score/history/{vendor_id}` — Score trend over time (last 20)
- `GET /api/credit-score/recommended-rate/{vendor_id}` — AI-suggested interest rate + eligible funding

---

## FEATURE 4: INVOICE FACTORING WITH RECOURSE OPTIONS
**Status:** ✅ IMPLEMENTED
**Files:** `services/factoring.py`, `routes/factoring.py`

### What it does:
Three factoring modes for different risk appetites:

**Option A: NON-RECOURSE (Lender takes all risk)**
- Interest: 18–24% (higher because lender bears default risk)
- If buyer doesn't pay → Lender absorbs loss
- Requires buyer credit check (CIBIL ≥ 650)
- Insurance premium: 2–3% added

**Option B: PARTIAL RECOURSE (50-50 risk sharing)**
- Interest: 14–18%
- If buyer defaults → Vendor pays 50%, Lender loses 50%
- Optional insurance for lender's 50%
- Most popular option

**Option C: FULL RECOURSE (Vendor guarantees)**
- Interest: 10–14% (lowest rate because vendor bears all risk)
- Vendor must repay even if buyer doesn't pay
- Requires personal guarantee + NPCI mandate
- Best rates for confident vendors

### Dynamic Pricing:
- Interest rate auto-calculated based on:
  - Recourse type
  - Vendor credit score
  - Buyer credit score
  - Invoice amount
  - Repayment period
  - Platform history

### Endpoints:
- `GET /api/factoring/options/{listing_id}` — Calculate rates for all 3 recourse options
- `POST /api/factoring/create` — Create factoring agreement with chosen recourse type
- `GET /api/factoring/agreement/{agreement_id}` — Get factoring agreement details
- `GET /api/factoring/vendor/{vendor_id}` — List all vendor's factoring agreements
- `GET /api/factoring/lender/{lender_id}` — List all lender's factoring agreements

---

## FEATURE 5: AUTO-REPAYMENT VIA NPCI e-MANDATE
**Status:** ✅ IMPLEMENTED
**Files:** `services/emandate.py`, `routes/emandate.py`

### What it does:
- Vendor registers NPCI e-Mandate during onboarding
- Bank authorizes recurring auto-debit up to a limit
- On due date → system triggers NPCI debit request
- If insufficient funds → auto-retry for 3 days
- Escalation workflow if all retries fail
- All mandate events logged on blockchain

### Mandate Lifecycle:
```
Register → Pending → Active → Debiting → Completed
                                 ↓
                           Failed → Retry (3x) → Escalated
```

### Endpoints:
- `POST /api/emandate/register` — Register new e-mandate
- `GET /api/emandate/mandate/{mandate_id}` — Get mandate details + recent executions
- `POST /api/emandate/mandate/{mandate_id}/pause` — Pause active mandate
- `POST /api/emandate/mandate/{mandate_id}/resume` — Resume paused mandate
- `POST /api/emandate/mandate/{mandate_id}/revoke` — Permanently revoke mandate
- `POST /api/emandate/execute` — Execute auto-debit for specific installment
- `POST /api/emandate/retry-failed` — Batch retry all failed debits (cron endpoint)
- `GET /api/emandate/vendor/{vendor_id}` — List vendor's mandates

---

## INTEGRATION: SANDBOX.CO.IN GST API
**Status:** ✅ INTEGRATED & TESTED
**Config:** `.env` → `Sandbox_API_KEYNAME`, `Sandbox_API_KEYNAME_SECRET`
**Auth:** POST `https://api.sandbox.co.in/authenticate` → JWT token (cached 23h)
**GSTIN:** POST `https://api.sandbox.co.in/gst/compliance/public/gstin/search`

### Used in:
- Triple Verification Engine (live GSTIN lookup — returns legal name, trade name, status, address)
- Falls back to mock verification if API unavailable
- Token is NOT Bearer — passed raw in Authorization header

---

## EXISTING FEATURES PRESERVED:
- ✅ User authentication (JWT + OTP)
- ✅ Vendor registration & KYC
- ✅ GST-compliant invoice creation
- ✅ PDF generation & email
- ✅ Marketplace listings
- ✅ Lender management
- ✅ InvoX Pay payment gateway
- ✅ Repayment schedules
- ✅ Blockchain ledger (PoW + signatures)
- ✅ Notifications system
- ✅ Activity logging
- ✅ Dashboard analytics
- ✅ Government API verification (mock)
- ✅ Smart contract PDFs

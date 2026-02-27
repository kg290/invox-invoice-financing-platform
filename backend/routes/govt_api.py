"""
Government Verification API Routes (Sandbox.co.in)
───────────────────────────────────────────────────
Real Indian government verification via Sandbox.co.in production APIs:
  • POST /api/govt/verify-gstin         — GST portal GSTIN search
  • POST /api/govt/verify-aadhaar       — Aadhaar format validation
  • POST /api/govt/aadhaar/generate-otp — Aadhaar e-KYC step 1 (send OTP)
  • POST /api/govt/aadhaar/verify-otp   — Aadhaar e-KYC step 2 (verify OTP)
  • POST /api/govt/verify-pan           — NSDL PAN verification
  • POST /api/govt/fetch-cibil          — Credit score assessment
  • POST /api/govt/verify-bank          — Bank account penny-less verification
  • POST /api/govt/verify-ifsc          — IFSC code verification
  • POST /api/govt/verify-all           — Full cross-verification pipeline
  • GET  /api/govt/health               — Sandbox API connectivity test

All endpoints hit REAL Sandbox.co.in APIs. No mock databases.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from services.govt_verification import (
    verify_gstin_govt,
    verify_aadhaar_govt,
    generate_aadhaar_otp_govt,
    verify_aadhaar_otp_govt,
    verify_pan_govt,
    fetch_cibil_score,
    verify_bank_account_govt,
    verify_ifsc_code,
    run_govt_verification,
)
from services.sandbox_client import test_connection

router = APIRouter(prefix="/api/govt", tags=["Government Verification APIs (Sandbox.co.in)"])


# ── Request Models ──

class GSTINVerifyRequest(BaseModel):
    gstin: str = Field(..., min_length=15, max_length=15)

class AadhaarVerifyRequest(BaseModel):
    aadhaar: str = Field(..., min_length=12, max_length=12)

class PANVerifyRequest(BaseModel):
    pan: str = Field(..., min_length=10, max_length=10)

class CIBILFetchRequest(BaseModel):
    pan: str = Field(..., min_length=10, max_length=10)

class BankVerifyRequest(BaseModel):
    account_number: str = Field(..., min_length=8, max_length=20)
    ifsc: str = Field(..., min_length=11, max_length=11)

class IFSCVerifyRequest(BaseModel):
    ifsc: str = Field(..., min_length=11, max_length=11)

class AadhaarOTPGenerateRequest(BaseModel):
    aadhaar: str = Field(..., min_length=12, max_length=12)

class AadhaarOTPVerifyRequest(BaseModel):
    reference_id: str = Field(..., min_length=1)
    otp: str = Field(..., min_length=4, max_length=6)

class FullVerifyRequest(BaseModel):
    """All vendor data needed for comprehensive verification."""
    full_name: str
    date_of_birth: str
    personal_pan: str
    personal_aadhaar: str
    gstin: str
    business_name: str
    bank_account_number: str
    bank_ifsc: str


# ── Endpoints (all hit real Sandbox.co.in APIs) ──

@router.post("/verify-gstin")
def api_verify_gstin(req: GSTINVerifyRequest):
    """Verify a GSTIN via Sandbox.co.in GST Search API."""
    result = verify_gstin_govt(req.gstin.upper())
    return result.to_dict()


@router.post("/verify-aadhaar")
def api_verify_aadhaar(req: AadhaarVerifyRequest):
    """Validate Aadhaar number format. Use OTP endpoints for full e-KYC."""
    result = verify_aadhaar_govt(req.aadhaar)
    return result.to_dict()


@router.post("/aadhaar/generate-otp")
def api_aadhaar_generate_otp(req: AadhaarOTPGenerateRequest):
    """
    Aadhaar e-KYC Step 1: Generate OTP via Sandbox.co.in.
    Sends OTP to the mobile number registered with UIDAI.
    Returns a reference_id needed for step 2 (verify-otp).
    """
    result = generate_aadhaar_otp_govt(req.aadhaar)
    return result.to_dict()


@router.post("/aadhaar/verify-otp")
def api_aadhaar_verify_otp(req: AadhaarOTPVerifyRequest):
    """
    Aadhaar e-KYC Step 2: Verify OTP and retrieve full e-KYC data.
    Returns name, DOB, address, gender, photo from UIDAI records.
    """
    result = verify_aadhaar_otp_govt(req.reference_id, req.otp)
    return result.to_dict()


@router.post("/verify-pan")
def api_verify_pan(req: PANVerifyRequest):
    """Verify a PAN via Sandbox.co.in PAN Verification API."""
    result = verify_pan_govt(req.pan.upper())
    return result.to_dict()


@router.post("/fetch-cibil")
def api_fetch_cibil(req: CIBILFetchRequest):
    """Fetch credit score assessment (internal scoring + PAN verification)."""
    result = fetch_cibil_score(req.pan.upper())
    return result.to_dict()


@router.post("/verify-bank")
def api_verify_bank(req: BankVerifyRequest):
    """Verify a bank account via Sandbox.co.in Penny-Less verification."""
    result = verify_bank_account_govt(req.account_number, req.ifsc.upper())
    return result.to_dict()


@router.post("/verify-ifsc")
def api_verify_ifsc(req: IFSCVerifyRequest):
    """Verify IFSC code and get bank branch details via Sandbox.co.in."""
    result = verify_ifsc_code(req.ifsc.upper())
    return result.to_dict()


@router.post("/verify-all")
def api_verify_all(req: FullVerifyRequest):
    """
    Run the FULL government cross-verification pipeline via Sandbox.co.in.
    Checks GST, Aadhaar, PAN, Credit Score, and Bank — all at once.
    Cross-verifies names, DOB, PAN-Aadhaar linkage, GST registration, etc.

    All checks hit REAL Sandbox.co.in APIs (no mock data).

    Returns:
      - overall_status: "verified" | "rejected" | "needs_review"
      - cibil_score: estimated credit score
      - checks: detailed list of all checks run
      - errors: list of failed check reasons
      - auto_filled: data auto-populated from government APIs
    """
    vendor_data = req.model_dump()
    result = run_govt_verification(vendor_data)
    return result


@router.get("/health")
def api_health():
    """Test Sandbox.co.in API connectivity."""
    return test_connection()

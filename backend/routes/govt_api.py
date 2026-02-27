"""
Mock Government API Routes
───────────────────────────
Exposes REST endpoints that simulate real Indian government APIs:
  • POST /api/govt/verify-gstin       — GST portal lookup
  • POST /api/govt/verify-aadhaar     — UIDAI Aadhaar verification
  • POST /api/govt/verify-pan         — NSDL PAN verification
  • POST /api/govt/fetch-cibil        — CIBIL credit score lookup
  • POST /api/govt/verify-bank        — Bank account verification
  • POST /api/govt/verify-all         — Run full cross-verification

These are called BEFORE vendor registration to validate all data.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from services.govt_verification import (
    verify_gstin_govt,
    verify_aadhaar_govt,
    verify_pan_govt,
    fetch_cibil_score,
    verify_bank_account_govt,
    run_govt_verification,
)

router = APIRouter(prefix="/api/govt", tags=["Government Verification APIs"])


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


# ── Endpoints ──

@router.post("/verify-gstin")
def api_verify_gstin(req: GSTINVerifyRequest):
    """Verify a GSTIN against the GST portal database."""
    result = verify_gstin_govt(req.gstin.upper())
    return result.to_dict()


@router.post("/verify-aadhaar")
def api_verify_aadhaar(req: AadhaarVerifyRequest):
    """Verify an Aadhaar number against UIDAI records."""
    result = verify_aadhaar_govt(req.aadhaar)
    return result.to_dict()


@router.post("/verify-pan")
def api_verify_pan(req: PANVerifyRequest):
    """Verify a PAN against NSDL records."""
    result = verify_pan_govt(req.pan.upper())
    return result.to_dict()


@router.post("/fetch-cibil")
def api_fetch_cibil(req: CIBILFetchRequest):
    """Fetch CIBIL credit score using PAN number."""
    result = fetch_cibil_score(req.pan.upper())
    return result.to_dict()


@router.post("/verify-bank")
def api_verify_bank(req: BankVerifyRequest):
    """Verify a bank account against banking records."""
    result = verify_bank_account_govt(req.account_number, req.ifsc.upper())
    return result.to_dict()


@router.post("/verify-all")
def api_verify_all(req: FullVerifyRequest):
    """
    Run the FULL government cross-verification pipeline.
    Checks GST, Aadhaar, PAN, CIBIL, and Bank — all at once.
    Cross-verifies names, DOB, PAN-Aadhaar linkage, GST registration, etc.

    Returns:
      - overall_status: "verified" | "rejected" | "needs_review"
      - cibil_score: auto-fetched score
      - checks: detailed list of all checks run
      - errors: list of failed check reasons
      - auto_filled: data auto-populated from government records
    """
    vendor_data = req.model_dump()
    result = run_govt_verification(vendor_data)
    return result

"""
InvoX — Sandbox.co.in API Client
═════════════════════════════════
Production-grade client for Sandbox.co.in government verification APIs.

Handles:
  • JWT Authentication (24-hour token caching)
  • GST Search (GSTIN verification)
  • PAN Verification
  • Aadhaar e-KYC (OTP Generate + Verify)
  • Bank Account Verification (Penny-Less)
  • IFSC Verification

Docs: https://developer.sandbox.co.in
"""

import os
import time
import logging
from typing import Optional
from dotenv import load_dotenv
import httpx

load_dotenv()

logger = logging.getLogger("sandbox_client")

# ════════════════════════════════════════════════════════════════════
#  CONFIGURATION
# ════════════════════════════════════════════════════════════════════

SANDBOX_BASE_URL = "https://api.sandbox.co.in"
SANDBOX_API_KEY = os.getenv("SANDBOX_API_KEYNAME", "")
SANDBOX_API_SECRET = os.getenv("SANDBOX_API_KEYNAME_SECRET", "")

# Token cache
_cached_token: Optional[str] = None
_token_expires_at: float = 0.0  # Unix timestamp


# ════════════════════════════════════════════════════════════════════
#  AUTHENTICATION
# ════════════════════════════════════════════════════════════════════

def _get_auth_token() -> str:
    """
    Authenticate with Sandbox.co.in and return a JWT access token.
    Caches the token and refreshes when near expiry (23-hour window).
    """
    global _cached_token, _token_expires_at

    # Return cached token if still valid (with 1-hour buffer)
    if _cached_token and time.time() < (_token_expires_at - 3600):
        return _cached_token

    if not SANDBOX_API_KEY or not SANDBOX_API_SECRET:
        raise RuntimeError(
            "Sandbox API credentials not configured. "
            "Set SANDBOX_API_KEYNAME and SANDBOX_API_KEYNAME_SECRET in .env"
        )

    logger.info("Authenticating with Sandbox.co.in...")
    resp = httpx.post(
        f"{SANDBOX_BASE_URL}/authenticate",
        headers={
            "x-api-key": SANDBOX_API_KEY,
            "x-api-secret": SANDBOX_API_SECRET,
            "Content-Type": "application/json",
        },
        timeout=15.0,
    )

    if resp.status_code != 200:
        raise RuntimeError(f"Sandbox authentication failed: {resp.status_code} — {resp.text}")

    data = resp.json()
    _cached_token = data.get("access_token") or data.get("data", {}).get("access_token")
    if not _cached_token:
        raise RuntimeError(f"No access_token in Sandbox auth response: {data}")

    # Token is valid for 24 hours
    _token_expires_at = time.time() + (24 * 3600)
    logger.info("Sandbox authentication successful — token cached for 24h")
    return _cached_token


def _auth_headers() -> dict:
    """Return headers required for authenticated Sandbox API calls."""
    token = _get_auth_token()
    return {
        "Authorization": token,          # NOT "Bearer <token>" — Sandbox requirement
        "x-api-key": SANDBOX_API_KEY,
        "Content-Type": "application/json",
    }


# ════════════════════════════════════════════════════════════════════
#  GST — Search GSTIN
# ════════════════════════════════════════════════════════════════════

def search_gstin(gstin: str) -> dict:
    """
    Verify GST-registered business by GSTIN.

    Endpoint: POST /gst/compliance/public/gstin/search
    Returns full GST registration details.

    Returns dict with keys:
      success (bool), data (dict | None), error (str | None)
    """
    try:
        headers = _auth_headers()
        headers["x-api-version"] = "1.0.0"

        resp = httpx.post(
            f"{SANDBOX_BASE_URL}/gst/compliance/public/gstin/search",
            headers=headers,
            json={"gstin": gstin.strip().upper()},
            timeout=30.0,
        )

        body = resp.json()

        if resp.status_code != 200 or body.get("code") != 200:
            error_msg = body.get("message") or body.get("error") or f"Status {resp.status_code}"
            return {"success": False, "data": None, "error": f"GSTIN lookup failed: {error_msg}"}

        gst_data = body.get("data", {}).get("data", {})
        if not gst_data:
            return {"success": False, "data": None, "error": f"No GST records found for {gstin}"}

        # Normalize response to our internal format
        address_info = gst_data.get("pradr", {}).get("addr", {})
        full_address = ", ".join(filter(None, [
            address_info.get("bno", ""),
            address_info.get("flno", ""),
            address_info.get("st", ""),
            address_info.get("loc", ""),
            address_info.get("dst", ""),
            address_info.get("stcd", ""),
            address_info.get("pncd", ""),
        ]))

        return {
            "success": True,
            "data": {
                "gstin": gst_data.get("gstin", gstin),
                "legal_name": gst_data.get("lgnm", ""),
                "trade_name": gst_data.get("tradeNam", ""),
                "registration_date": gst_data.get("rgdt", ""),
                "status": "Active" if gst_data.get("sts", "").lower() == "active" else gst_data.get("sts", "Unknown"),
                "business_type": gst_data.get("ctb", ""),
                "state_code": gst_data.get("stcd", ""),
                "state": address_info.get("stcd", ""),
                "filing_frequency": "Monthly",  # Not directly in response
                "total_filings": 0,  # Not in search response
                "compliance_rating": "Regular" if gst_data.get("sts", "").lower() == "active" else "Defaulter",
                "last_filing_date": gst_data.get("lstupdt", ""),
                "annual_turnover_declared": 0,  # Not in public search
                "address": full_address,
                "pan_linked": gst_data.get("gstin", "")[2:12] if len(gst_data.get("gstin", "")) >= 12 else "",
                "dealer_type": gst_data.get("dty", ""),
                "nature_of_business": gst_data.get("nba", []),
                "einvoice_status": gst_data.get("einvoiceStatus", ""),
            },
            "error": None,
            "raw": gst_data,  # Keep raw response for debugging
        }

    except httpx.TimeoutException:
        return {"success": False, "data": None, "error": "GST API timed out. Please try again."}
    except Exception as e:
        logger.exception("GSTIN search error")
        return {"success": False, "data": None, "error": f"GST verification error: {str(e)}"}


# ════════════════════════════════════════════════════════════════════
#  PAN — Verify PAN Details
# ════════════════════════════════════════════════════════════════════

def verify_pan(pan: str, name: str = "", date_of_birth: str = "") -> dict:
    """
    Verify PAN number and holder information.

    Endpoint: POST /kyc/pan/verify
    Body requires: @entity, pan, name_as_per_pan, date_of_birth, consent, reason

    Args:
        pan: 10-character PAN
        name: Name as per PAN card
        date_of_birth: DD/MM/YYYY format

    Returns dict with keys:
      success (bool), data (dict | None), error (str | None)
    """
    try:
        headers = _auth_headers()

        payload = {
            "@entity": "in.co.sandbox.kyc.pan_verification.request",
            "pan": pan.strip().upper(),
            "name_as_per_pan": name.strip().upper() if name else "NA",
            "date_of_birth": date_of_birth if date_of_birth else "01/01/2000",
            "consent": "Y",
            "reason": "KYC verification for invoice financing platform",
        }

        resp = httpx.post(
            f"{SANDBOX_BASE_URL}/kyc/pan/verify",
            headers=headers,
            json=payload,
            timeout=30.0,
        )

        body = resp.json()

        if resp.status_code != 200 or body.get("code") != 200:
            error_msg = body.get("message") or body.get("error") or f"Status {resp.status_code}"
            return {"success": False, "data": None, "error": f"PAN verification failed: {error_msg}"}

        pan_data = body.get("data", {})

        return {
            "success": True,
            "data": {
                "pan": pan_data.get("pan", pan),
                "full_name": name.upper() if name else "",
                "category": pan_data.get("category", ""),
                "status": "Active" if pan_data.get("status", "").lower() == "valid" else pan_data.get("status", "Unknown"),
                "name_match": pan_data.get("name_as_per_pan_match", False),
                "dob_match": pan_data.get("date_of_birth_match", False),
                "aadhaar_seeding_status": pan_data.get("aadhaar_seeding_status", ""),
                "pan_type": "P" if pan_data.get("category", "").lower() == "individual" else "C",
            },
            "error": None,
        }

    except httpx.TimeoutException:
        return {"success": False, "data": None, "error": "PAN API timed out. Please try again."}
    except Exception as e:
        logger.exception("PAN verification error")
        return {"success": False, "data": None, "error": f"PAN verification error: {str(e)}"}


# ════════════════════════════════════════════════════════════════════
#  AADHAAR — Generate OTP + Verify OTP
# ════════════════════════════════════════════════════════════════════

def aadhaar_generate_otp(aadhaar_number: str) -> dict:
    """
    Generate OTP for Aadhaar Offline e-KYC.

    Endpoint: POST /kyc/aadhaar/okyc/otp
    Returns reference_id needed for OTP verification.

    Returns dict with keys:
      success (bool), reference_id (str | None), error (str | None)
    """
    try:
        headers = _auth_headers()

        payload = {
            "@entity": "in.co.sandbox.kyc.aadhaar.okyc.otp.request",
            "aadhaar_number": aadhaar_number.strip(),
            "consent": "Y",
            "reason": "KYC verification for invoice financing platform",
        }

        resp = httpx.post(
            f"{SANDBOX_BASE_URL}/kyc/aadhaar/okyc/otp",
            headers=headers,
            json=payload,
            timeout=30.0,
        )

        body = resp.json()

        if resp.status_code != 200 or body.get("code") != 200:
            error_msg = body.get("message") or body.get("error") or f"Status {resp.status_code}"
            return {"success": False, "reference_id": None, "error": f"Aadhaar OTP generation failed: {error_msg}"}

        ref_id = body.get("data", {}).get("reference_id")
        return {
            "success": True,
            "reference_id": str(ref_id) if ref_id else None,
            "message": body.get("data", {}).get("message", "OTP sent successfully"),
            "error": None,
        }

    except httpx.TimeoutException:
        return {"success": False, "reference_id": None, "error": "Aadhaar OTP API timed out."}
    except Exception as e:
        logger.exception("Aadhaar OTP generation error")
        return {"success": False, "reference_id": None, "error": f"Aadhaar OTP error: {str(e)}"}


def aadhaar_verify_otp(reference_id: str, otp: str) -> dict:
    """
    Verify Aadhaar OTP and retrieve e-KYC data.

    Endpoint: POST /kyc/aadhaar/okyc/otp/verify
    Returns full Aadhaar details (name, DOB, address, photo).

    Returns dict with keys:
      success (bool), data (dict | None), error (str | None)
    """
    try:
        headers = _auth_headers()

        payload = {
            "@entity": "in.co.sandbox.kyc.aadhaar.okyc.request",
            "reference_id": reference_id,
            "otp": otp.strip(),
        }

        resp = httpx.post(
            f"{SANDBOX_BASE_URL}/kyc/aadhaar/okyc/otp/verify",
            headers=headers,
            json=payload,
            timeout=30.0,
        )

        body = resp.json()

        if resp.status_code != 200 or body.get("code") != 200:
            error_msg = body.get("message") or body.get("error") or f"Status {resp.status_code}"
            return {"success": False, "data": None, "error": f"Aadhaar OTP verification failed: {error_msg}"}

        aadhaar_data = body.get("data", {})
        address = aadhaar_data.get("address", {})

        return {
            "success": True,
            "data": {
                "full_name": aadhaar_data.get("name", ""),
                "date_of_birth": aadhaar_data.get("date_of_birth", ""),
                "gender": aadhaar_data.get("gender", ""),
                "care_of": aadhaar_data.get("care_of", ""),
                "full_address": aadhaar_data.get("full_address", ""),
                "address": {
                    "house": address.get("house", ""),
                    "street": address.get("street", ""),
                    "landmark": address.get("landmark", ""),
                    "district": address.get("district", ""),
                    "state": address.get("state", ""),
                    "pincode": address.get("pincode", ""),
                    "country": address.get("country", "India"),
                },
                "year_of_birth": aadhaar_data.get("year_of_birth", ""),
                "photo": aadhaar_data.get("photo", ""),
                "is_active": True,
                "status": aadhaar_data.get("status", "VALID"),
            },
            "error": None,
        }

    except httpx.TimeoutException:
        return {"success": False, "data": None, "error": "Aadhaar verify API timed out."}
    except Exception as e:
        logger.exception("Aadhaar OTP verify error")
        return {"success": False, "data": None, "error": f"Aadhaar verify error: {str(e)}"}


# ════════════════════════════════════════════════════════════════════
#  BANK — Penny-Less Verification
# ════════════════════════════════════════════════════════════════════

def verify_bank_account(account_number: str, ifsc: str, name: str = "") -> dict:
    """
    Verify bank account via Penny-Less verification (no deposit needed).

    Endpoint: GET /bank/{ifsc}/accounts/{account_number}/penniless-verify

    Returns dict with keys:
      success (bool), data (dict | None), error (str | None)
    """
    try:
        headers = _auth_headers()

        url = f"{SANDBOX_BASE_URL}/bank/{ifsc.strip().upper()}/accounts/{account_number.strip()}/penniless-verify"
        params = {}
        if name:
            params["name"] = name.strip()

        resp = httpx.get(url, headers=headers, params=params, timeout=30.0)
        body = resp.json()

        if resp.status_code != 200 or body.get("code") != 200:
            error_msg = body.get("message") or body.get("error") or f"Status {resp.status_code}"
            return {"success": False, "data": None, "error": f"Bank verification failed: {error_msg}"}

        bank_data = body.get("data", {})
        account_exists = bank_data.get("account_exists", False)

        if not account_exists:
            return {
                "success": False,
                "data": None,
                "error": f"Bank account {account_number} does not exist at IFSC {ifsc}.",
            }

        return {
            "success": True,
            "data": {
                "account_number": account_number,
                "holder_name": bank_data.get("name_at_bank", ""),
                "ifsc": ifsc.upper(),
                "account_exists": True,
                "is_active": True,
            },
            "error": None,
        }

    except httpx.TimeoutException:
        return {"success": False, "data": None, "error": "Bank verification API timed out."}
    except Exception as e:
        logger.exception("Bank verification error")
        return {"success": False, "data": None, "error": f"Bank verification error: {str(e)}"}


# ════════════════════════════════════════════════════════════════════
#  BANK — IFSC Verification
# ════════════════════════════════════════════════════════════════════

def verify_ifsc(ifsc: str) -> dict:
    """
    Verify IFSC code and get bank branch details.

    Endpoint: GET /bank/{ifsc}

    Returns dict with keys:
      success (bool), data (dict | None), error (str | None)
    """
    try:
        headers = _auth_headers()

        resp = httpx.get(
            f"{SANDBOX_BASE_URL}/bank/{ifsc.strip().upper()}",
            headers=headers,
            timeout=15.0,
        )

        body = resp.json()

        if resp.status_code != 200:
            error_msg = body.get("message") or body.get("error") or f"Status {resp.status_code}"
            return {"success": False, "data": None, "error": f"IFSC verification failed: {error_msg}"}

        return {
            "success": True,
            "data": {
                "ifsc": body.get("IFSC", ifsc),
                "bank_name": body.get("BANK", ""),
                "branch": body.get("BRANCH", ""),
                "address": body.get("ADDRESS", ""),
                "city": body.get("CITY", ""),
                "state": body.get("STATE", ""),
                "district": body.get("DISTRICT", ""),
                "upi": body.get("UPI", False),
                "rtgs": body.get("RTGS", False),
                "neft": body.get("NEFT", False),
                "imps": body.get("IMPS", False),
            },
            "error": None,
        }

    except httpx.TimeoutException:
        return {"success": False, "data": None, "error": "IFSC verification API timed out."}
    except Exception as e:
        logger.exception("IFSC verification error")
        return {"success": False, "data": None, "error": f"IFSC verification error: {str(e)}"}


# ════════════════════════════════════════════════════════════════════
#  HEALTH CHECK — Test connectivity
# ════════════════════════════════════════════════════════════════════

def test_connection() -> dict:
    """Test Sandbox API connection by authenticating."""
    try:
        token = _get_auth_token()
        return {
            "connected": True,
            "message": "Sandbox.co.in API connected successfully",
            "token_preview": token[:20] + "..." if token else "N/A",
        }
    except Exception as e:
        return {
            "connected": False,
            "message": f"Connection failed: {str(e)}",
            "token_preview": None,
        }

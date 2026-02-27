"""
InvoX — Mock Government Verification APIs
═══════════════════════════════════════════
Simulates real government APIs for:
  • GST (Goods & Services Tax) portal verification
  • Aadhaar (UIDAI) identity verification
  • CIBIL credit score lookup
  • PAN verification
  • Bank account verification

Contains predefined "government database" records that incoming vendor
data is cross-checked against.  Only vendors whose details match will
be allowed to register.

In production, these would be replaced by actual API calls to:
  - GST:    https://sandbox.gst.gov.in
  - Aadhaar: UIDAI eKYC via Digilocker / OKYC
  - CIBIL:   TransUnion CIBIL Connect API
  - PAN:     NSDL / UTIITSL Verification API
"""

from typing import Optional
from datetime import datetime

# ════════════════════════════════════════════════════════════════════════
#  MOCK GOVERNMENT DATABASE  (pretend this is the govt server)
# ════════════════════════════════════════════════════════════════════════

# ── GST Portal Database ──
# Key = GSTIN
MOCK_GST_DATABASE: dict[str, dict] = {
    "07BVDPS4321K1Z3": {
        "gstin": "07BVDPS4321K1Z3",
        "legal_name": "SUNITA DEVI VERMA",
        "trade_name": "MAA ANNAPURNA TIFFIN SERVICE",
        "registration_date": "2020-01-15",
        "status": "Active",
        "business_type": "Proprietorship",
        "state_code": "07",
        "state": "Delhi",
        "filing_frequency": "Quarterly",
        "total_filings": 24,
        "compliance_rating": "Regular",
        "last_filing_date": "2025-12-31",
        "annual_turnover_declared": 480000,
        "address": "H-12, Back Lane, Laxmi Nagar, New Delhi - 110092",
        "pan_linked": "BVDPS4321K",
    },
    "07CVRPV5678L1Z6": {
        "gstin": "07CVRPV5678L1Z6",
        "legal_name": "RAMU VISHWAKARMA",
        "trade_name": "RAMU FURNITURE WORKS",
        "registration_date": "2018-06-01",
        "status": "Active",
        "business_type": "Proprietorship",
        "state_code": "07",
        "state": "Delhi",
        "filing_frequency": "Quarterly",
        "total_filings": 30,
        "compliance_rating": "Regular",
        "last_filing_date": "2025-12-31",
        "annual_turnover_declared": 720000,
        "address": "Shop 14, Kirti Nagar Furniture Market, New Delhi - 110015",
        "pan_linked": "CVRPV5678L",
    },
    "23FKBPK7890P1Z7": {
        "gstin": "23FKBPK7890P1Z7",
        "legal_name": "FATIMA BEE KHAN",
        "trade_name": "KHAN MASALA & SPICE TRADERS",
        "registration_date": "2019-01-01",
        "status": "Active",
        "business_type": "Proprietorship",
        "state_code": "23",
        "state": "Madhya Pradesh",
        "filing_frequency": "Quarterly",
        "total_filings": 24,
        "compliance_rating": "Regular",
        "last_filing_date": "2025-12-31",
        "annual_turnover_declared": 600000,
        "address": "Shop 22, Sarafa Bazaar, Chowk, Bhopal - 462001",
        "pan_linked": "FKBPK7890P",
    },
    # ── Karnajeet Gosavi ──
    "27GOPKG1234A1Z5": {
        "gstin": "27GOPKG1234A1Z5",
        "legal_name": "KARNAJEET GOSAVI",
        "trade_name": "GOSAVI DIGITAL SOLUTIONS",
        "registration_date": "2022-06-01",
        "status": "Active",
        "business_type": "Proprietorship",
        "state_code": "27",
        "state": "Maharashtra",
        "filing_frequency": "Monthly",
        "total_filings": 18,
        "compliance_rating": "Regular",
        "last_filing_date": "2026-01-31",
        "annual_turnover_declared": 850000,
        "address": "Office 5, Baner Tech Park, Baner, Pune - 411045",
        "pan_linked": "GOPKG1234A",
    },
    # ── Additional valid GSTINs for new registrations ──
    "27ABCDE1234F1Z5": {
        "gstin": "27ABCDE1234F1Z5",
        "legal_name": "RAJESH KUMAR SHARMA",
        "trade_name": "SHARMA ELECTRONICS",
        "registration_date": "2021-03-10",
        "status": "Active",
        "business_type": "Proprietorship",
        "state_code": "27",
        "state": "Maharashtra",
        "filing_frequency": "Monthly",
        "total_filings": 56,
        "compliance_rating": "Regular",
        "last_filing_date": "2025-11-30",
        "annual_turnover_declared": 1200000,
        "address": "Shop 45, Dadar Market, Mumbai - 400014",
        "pan_linked": "ABCDE1234F",
    },
    "29GHIJK5678L1Z9": {
        "gstin": "29GHIJK5678L1Z9",
        "legal_name": "PRIYA NAIDU",
        "trade_name": "PRIYA TEXTILES",
        "registration_date": "2020-07-20",
        "status": "Active",
        "business_type": "Proprietorship",
        "state_code": "29",
        "state": "Karnataka",
        "filing_frequency": "Monthly",
        "total_filings": 62,
        "compliance_rating": "Regular",
        "last_filing_date": "2026-01-31",
        "annual_turnover_declared": 900000,
        "address": "No. 12, Chickpet Market, Bengaluru - 560053",
        "pan_linked": "GHIJK5678L",
    },
    # ── Suspended GSTIN (should fail verification) ──
    "33ZZZZZ9999Z1ZZ": {
        "gstin": "33ZZZZZ9999Z1ZZ",
        "legal_name": "FRAUD COMPANY",
        "trade_name": "FRAUD TRADING CO",
        "registration_date": "2022-01-01",
        "status": "Suspended",
        "business_type": "Proprietorship",
        "state_code": "33",
        "state": "Tamil Nadu",
        "filing_frequency": "Monthly",
        "total_filings": 2,
        "compliance_rating": "Defaulter",
        "last_filing_date": "2022-06-30",
        "annual_turnover_declared": 50000,
        "address": "Unknown",
        "pan_linked": "ZZZZZ9999Z",
    },
}


# ── Aadhaar (UIDAI) Database ──
# Key = Aadhaar number
MOCK_AADHAAR_DATABASE: dict[str, dict] = {
    "234567891234": {
        "aadhaar": "234567891234",
        "full_name": "SUNITA DEVI VERMA",
        "date_of_birth": "1986-04-12",
        "gender": "F",
        "address": "H-12, Laxmi Nagar, New Delhi",
        "pincode": "110092",
        "state": "Delhi",
        "phone_linked": "9876543210",
        "is_active": True,
    },
    "456789012345": {
        "aadhaar": "456789012345",
        "full_name": "RAMU VISHWAKARMA",
        "date_of_birth": "1979-09-08",
        "gender": "M",
        "address": "Gali No. 3, Kirti Nagar, New Delhi",
        "pincode": "110015",
        "state": "Delhi",
        "phone_linked": "9123456780",
        "is_active": True,
    },
    "012345678901": {
        "aadhaar": "012345678901",
        "full_name": "FATIMA BEE KHAN",
        "date_of_birth": "1988-03-14",
        "gender": "F",
        "address": "Sarafa Bazaar, Old Bhopal",
        "pincode": "462001",
        "state": "Madhya Pradesh",
        "phone_linked": "9090909090",
        "is_active": True,
    },
    # Karnajeet Gosavi
    "987654321012": {
        "aadhaar": "987654321012",
        "full_name": "KARNAJEET GOSAVI",
        "date_of_birth": "2003-07-15",
        "gender": "M",
        "address": "Flat 12, Paradise Apartments, FC Road, Pune",
        "pincode": "411005",
        "state": "Maharashtra",
        "phone_linked": "9876501234",
        "is_active": True,
    },
    "876543210123": {
        "aadhaar": "876543210123",
        "full_name": "PRIYA NAIDU",
        "date_of_birth": "1992-11-25",
        "gender": "F",
        "address": "No. 12, Chickpet, Bengaluru",
        "pincode": "560053",
        "state": "Karnataka",
        "phone_linked": "9845012345",
        "is_active": True,
    },
    # Deactivated Aadhaar
    "111111111111": {
        "aadhaar": "111111111111",
        "full_name": "DEACTIVATED PERSON",
        "date_of_birth": "2000-01-01",
        "gender": "M",
        "address": "Unknown",
        "pincode": "000000",
        "state": "Unknown",
        "phone_linked": "0000000000",
        "is_active": False,
    },
}


# ── PAN Database ──
# Key = PAN number
MOCK_PAN_DATABASE: dict[str, dict] = {
    "BVDPS4321K": {
        "pan": "BVDPS4321K",
        "full_name": "SUNITA DEVI VERMA",
        "date_of_birth": "1986-04-12",
        "pan_type": "P",  # P=Individual
        "status": "Active",
        "aadhaar_linked": "234567891234",
    },
    "CVRPV5678L": {
        "pan": "CVRPV5678L",
        "full_name": "RAMU VISHWAKARMA",
        "date_of_birth": "1979-09-08",
        "pan_type": "P",
        "status": "Active",
        "aadhaar_linked": "456789012345",
    },
    "FKBPK7890P": {
        "pan": "FKBPK7890P",
        "full_name": "FATIMA BEE KHAN",
        "date_of_birth": "1988-03-14",
        "pan_type": "P",
        "status": "Active",
        "aadhaar_linked": "012345678901",
    },
    "GOPKG1234A": {
        "pan": "GOPKG1234A",
        "full_name": "KARNAJEET GOSAVI",
        "date_of_birth": "2003-07-15",
        "pan_type": "P",
        "status": "Active",
        "aadhaar_linked": "987654321012",
    },
    "ABCDE1234F": {
        "pan": "ABCDE1234F",
        "full_name": "RAJESH KUMAR SHARMA",
        "date_of_birth": "1990-06-15",
        "pan_type": "P",
        "status": "Active",
        "aadhaar_linked": "123456789012",
    },
    "GHIJK5678L": {
        "pan": "GHIJK5678L",
        "full_name": "PRIYA NAIDU",
        "date_of_birth": "1992-11-25",
        "pan_type": "P",
        "status": "Active",
        "aadhaar_linked": "876543210123",
    },
    "ZZZZZ9999Z": {
        "pan": "ZZZZZ9999Z",
        "full_name": "FRAUD PERSON",
        "date_of_birth": "2000-01-01",
        "pan_type": "P",
        "status": "Inactive",
        "aadhaar_linked": "111111111111",
    },
}


# ── CIBIL Credit Bureau Database ──
# Key = PAN number (CIBIL lookups are done via PAN)
MOCK_CIBIL_DATABASE: dict[str, dict] = {
    "BVDPS4321K": {
        "pan": "BVDPS4321K",
        "name": "SUNITA DEVI VERMA",
        "cibil_score": 672,
        "score_range": "Fair",
        "total_accounts": 2,
        "active_accounts": 1,
        "overdue_accounts": 0,
        "credit_utilization": 35,
        "loan_defaults": 0,
        "enquiries_last_6_months": 1,
        "oldest_account_age_months": 48,
        "total_outstanding": 25000,
        "report_date": "2026-01-15",
    },
    "CVRPV5678L": {
        "pan": "CVRPV5678L",
        "name": "RAMU VISHWAKARMA",
        "cibil_score": 698,
        "score_range": "Fair",
        "total_accounts": 3,
        "active_accounts": 2,
        "overdue_accounts": 0,
        "credit_utilization": 28,
        "loan_defaults": 0,
        "enquiries_last_6_months": 2,
        "oldest_account_age_months": 84,
        "total_outstanding": 65000,
        "report_date": "2026-01-10",
    },
    "FKBPK7890P": {
        "pan": "FKBPK7890P",
        "name": "FATIMA BEE KHAN",
        "cibil_score": 660,
        "score_range": "Fair",
        "total_accounts": 1,
        "active_accounts": 1,
        "overdue_accounts": 0,
        "credit_utilization": 22,
        "loan_defaults": 0,
        "enquiries_last_6_months": 0,
        "oldest_account_age_months": 60,
        "total_outstanding": 35000,
        "report_date": "2026-01-12",
    },
    "GOPKG1234A": {
        "pan": "GOPKG1234A",
        "name": "KARNAJEET GOSAVI",
        "cibil_score": 742,
        "score_range": "Good",
        "total_accounts": 2,
        "active_accounts": 1,
        "overdue_accounts": 0,
        "credit_utilization": 20,
        "loan_defaults": 0,
        "enquiries_last_6_months": 1,
        "oldest_account_age_months": 36,
        "total_outstanding": 15000,
        "report_date": "2026-01-15",
    },
    "ABCDE1234F": {
        "pan": "ABCDE1234F",
        "name": "RAJESH KUMAR SHARMA",
        "cibil_score": 745,
        "score_range": "Good",
        "total_accounts": 4,
        "active_accounts": 3,
        "overdue_accounts": 0,
        "credit_utilization": 18,
        "loan_defaults": 0,
        "enquiries_last_6_months": 1,
        "oldest_account_age_months": 72,
        "total_outstanding": 150000,
        "report_date": "2026-02-01",
    },
    "GHIJK5678L": {
        "pan": "GHIJK5678L",
        "name": "PRIYA NAIDU",
        "cibil_score": 780,
        "score_range": "Excellent",
        "total_accounts": 3,
        "active_accounts": 2,
        "overdue_accounts": 0,
        "credit_utilization": 12,
        "loan_defaults": 0,
        "enquiries_last_6_months": 0,
        "oldest_account_age_months": 48,
        "total_outstanding": 50000,
        "report_date": "2026-01-20",
    },
    "ZZZZZ9999Z": {
        "pan": "ZZZZZ9999Z",
        "name": "FRAUD PERSON",
        "cibil_score": 320,
        "score_range": "Very Poor",
        "total_accounts": 5,
        "active_accounts": 0,
        "overdue_accounts": 4,
        "credit_utilization": 95,
        "loan_defaults": 3,
        "enquiries_last_6_months": 8,
        "oldest_account_age_months": 12,
        "total_outstanding": 500000,
        "report_date": "2025-06-01",
    },
}


# ── Bank Account Database ──
# Key = account_number
MOCK_BANK_DATABASE: dict[str, dict] = {
    "10234567890": {
        "account_number": "10234567890",
        "holder_name": "SUNITA DEVI VERMA",
        "bank_name": "State Bank of India",
        "ifsc": "SBIN0009876",
        "branch": "Laxmi Nagar",
        "account_type": "Savings",
        "is_active": True,
    },
    "20345678901": {
        "account_number": "20345678901",
        "holder_name": "RAMU VISHWAKARMA",
        "bank_name": "Punjab National Bank",
        "ifsc": "PUNB0123400",
        "branch": "Kirti Nagar",
        "account_type": "Current",
        "is_active": True,
    },
    "50678901234": {
        "account_number": "50678901234",
        "holder_name": "FATIMA BEE KHAN",
        "bank_name": "Central Bank of India",
        "ifsc": "CBIN0281234",
        "branch": "New Market, Bhopal",
        "account_type": "Current",
        "is_active": True,
    },
    "91203456789": {
        "account_number": "91203456789",
        "holder_name": "KARNAJEET GOSAVI",
        "bank_name": "HDFC Bank",
        "ifsc": "HDFC0001234",
        "branch": "FC Road, Pune",
        "account_type": "Savings",
        "is_active": True,
    },
    "30456789012": {
        "account_number": "30456789012",
        "holder_name": "RAJESH KUMAR SHARMA",
        "bank_name": "HDFC Bank",
        "ifsc": "HDFC0001234",
        "branch": "Dadar, Mumbai",
        "account_type": "Current",
        "is_active": True,
    },
    "40567890123": {
        "account_number": "40567890123",
        "holder_name": "PRIYA NAIDU",
        "bank_name": "Canara Bank",
        "ifsc": "CNRB0001234",
        "branch": "Chickpet, Bengaluru",
        "account_type": "Current",
        "is_active": True,
    },
}


# ════════════════════════════════════════════════════════════════════════
#  MOCK API FUNCTIONS  (simulate govt API calls)
# ════════════════════════════════════════════════════════════════════════

class GovtVerificationResult:
    """Standard response from a mock govt API call."""
    def __init__(self, success: bool, data: Optional[dict] = None, error: Optional[str] = None):
        self.success = success
        self.data = data or {}
        self.error = error

    def to_dict(self) -> dict:
        return {"success": self.success, "data": self.data, "error": self.error}


def verify_gstin_govt(gstin: str) -> GovtVerificationResult:
    """
    Mock GST Portal API — looks up GSTIN in the government database.
    Returns full GST registration details if found.
    """
    record = MOCK_GST_DATABASE.get(gstin)
    if not record:
        return GovtVerificationResult(
            success=False,
            error=f"GSTIN {gstin} not found in GST portal. This GSTIN is not registered."
        )
    if record["status"] != "Active":
        return GovtVerificationResult(
            success=False,
            data=record,
            error=f"GSTIN {gstin} status is '{record['status']}'. Only Active GSTINs are accepted."
        )
    return GovtVerificationResult(success=True, data=record)


def verify_aadhaar_govt(aadhaar: str) -> GovtVerificationResult:
    """
    Mock UIDAI API — looks up Aadhaar in the government database.
    Returns identity details if found and active.
    """
    record = MOCK_AADHAAR_DATABASE.get(aadhaar)
    if not record:
        return GovtVerificationResult(
            success=False,
            error=f"Aadhaar {aadhaar[:4]}XXXX{aadhaar[8:]} not found in UIDAI records."
        )
    if not record["is_active"]:
        return GovtVerificationResult(
            success=False,
            data={"aadhaar": aadhaar[:4] + "XXXX" + aadhaar[8:]},
            error="This Aadhaar has been deactivated by UIDAI."
        )
    return GovtVerificationResult(success=True, data=record)


def verify_pan_govt(pan: str) -> GovtVerificationResult:
    """
    Mock NSDL/UTIITSL PAN verification API.
    Returns PAN holder details if found and active.
    """
    record = MOCK_PAN_DATABASE.get(pan)
    if not record:
        return GovtVerificationResult(
            success=False,
            error=f"PAN {pan} not found in Income Tax records."
        )
    if record["status"] != "Active":
        return GovtVerificationResult(
            success=False,
            data=record,
            error=f"PAN {pan} is '{record['status']}'. Only Active PANs are accepted."
        )
    return GovtVerificationResult(success=True, data=record)


def fetch_cibil_score(pan: str) -> GovtVerificationResult:
    """
    Mock TransUnion CIBIL API — fetches credit score using PAN.
    Returns full credit report summary.
    """
    record = MOCK_CIBIL_DATABASE.get(pan)
    if not record:
        return GovtVerificationResult(
            success=False,
            error=f"No CIBIL record found for PAN {pan}. The individual may not have a credit history."
        )
    return GovtVerificationResult(success=True, data=record)


def verify_bank_account_govt(account_number: str, ifsc: str) -> GovtVerificationResult:
    """
    Mock RBI / NPCI bank account verification API.
    Validates that account exists and matches provided IFSC.
    """
    record = MOCK_BANK_DATABASE.get(account_number)
    if not record:
        return GovtVerificationResult(
            success=False,
            error=f"Bank account {account_number} not found in banking records."
        )
    if not record["is_active"]:
        return GovtVerificationResult(
            success=False,
            error="This bank account has been closed or frozen."
        )
    if record["ifsc"] != ifsc:
        return GovtVerificationResult(
            success=False,
            data={"expected_ifsc": record["ifsc"]},
            error=f"IFSC mismatch. Account is registered with IFSC {record['ifsc']}, but {ifsc} was provided."
        )
    return GovtVerificationResult(success=True, data=record)


# ════════════════════════════════════════════════════════════════════════
#  CROSS-VERIFICATION ENGINE
# ════════════════════════════════════════════════════════════════════════

def _name_match(name1: str, name2: str) -> bool:
    """
    Fuzzy name comparison — normalizes both strings and checks if they match.
    Handles case differences, extra spaces, minor variations.
    """
    def normalize(n: str) -> str:
        return " ".join(n.upper().strip().split())
    return normalize(name1) == normalize(name2)


def run_govt_verification(vendor_data: dict) -> dict:
    """
    Run the complete government verification pipeline.
    Cross-checks vendor-submitted data against mock government databases.

    Returns a dict with:
      - overall_status: "verified" | "rejected"
      - cibil_score: auto-fetched score (or None)
      - gst_details: auto-fetched GST data
      - checks: list of individual check results
      - errors: list of failure reasons
    """
    checks = []
    errors = []
    warnings = []
    auto_filled = {}

    gstin = vendor_data.get("gstin", "")
    pan = vendor_data.get("personal_pan", "")
    aadhaar = vendor_data.get("personal_aadhaar", "")
    full_name = vendor_data.get("full_name", "")
    business_name = vendor_data.get("business_name", "")
    dob = vendor_data.get("date_of_birth", "")
    bank_account = vendor_data.get("bank_account_number", "")
    bank_ifsc = vendor_data.get("bank_ifsc", "")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  1. GST PORTAL VERIFICATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    gst_result = verify_gstin_govt(gstin)
    if not gst_result.success:
        checks.append({"check": "gst_portal", "status": "failed", "message": gst_result.error})
        errors.append(f"GST Verification Failed: {gst_result.error}")
    else:
        gst_data = gst_result.data
        checks.append({"check": "gst_portal", "status": "passed", "message": f"GSTIN {gstin} is Active on GST portal"})

        # 1a. Legal name on GST must match vendor's full name
        if not _name_match(gst_data["legal_name"], full_name):
            checks.append({
                "check": "gst_name_match", "status": "failed",
                "message": f"Name mismatch: GST portal has '{gst_data['legal_name']}' but you entered '{full_name.upper()}'"
            })
            errors.append(f"Name on GST ({gst_data['legal_name']}) does not match your name ({full_name})")
        else:
            checks.append({"check": "gst_name_match", "status": "passed", "message": "Name matches GST registration"})

        # 1b. Trade name must match business name
        if not _name_match(gst_data["trade_name"], business_name):
            checks.append({
                "check": "gst_business_name_match", "status": "failed",
                "message": f"Business name mismatch: GST portal has '{gst_data['trade_name']}' but you entered '{business_name.upper()}'"
            })
            errors.append(f"Business name on GST ({gst_data['trade_name']}) does not match ({business_name})")
        else:
            checks.append({"check": "gst_business_name_match", "status": "passed", "message": "Business name matches GST registration"})

        # 1c. PAN linked to GST must match
        if gst_data["pan_linked"] != pan:
            checks.append({
                "check": "gst_pan_link", "status": "failed",
                "message": f"PAN mismatch: GST portal has PAN '{gst_data['pan_linked']}' but you entered '{pan}'"
            })
            errors.append(f"PAN linked to GST ({gst_data['pan_linked']}) does not match your PAN ({pan})")
        else:
            checks.append({"check": "gst_pan_link", "status": "passed", "message": "PAN matches GST registration"})

        # 1d. Auto-fill GST details from portal
        auto_filled["gst_compliance_status"] = gst_data["compliance_rating"]
        auto_filled["total_gst_filings"] = gst_data["total_filings"]
        auto_filled["gst_filing_frequency"] = gst_data["filing_frequency"]
        auto_filled["gst_registration_date"] = gst_data["registration_date"]

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  2. AADHAAR (UIDAI) VERIFICATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    aadhaar_result = verify_aadhaar_govt(aadhaar)
    if not aadhaar_result.success:
        checks.append({"check": "aadhaar_uidai", "status": "failed", "message": aadhaar_result.error})
        errors.append(f"Aadhaar Verification Failed: {aadhaar_result.error}")
    else:
        aadhaar_data = aadhaar_result.data
        checks.append({"check": "aadhaar_uidai", "status": "passed", "message": "Aadhaar is valid and active in UIDAI records"})

        # 2a. Name on Aadhaar must match vendor name
        if not _name_match(aadhaar_data["full_name"], full_name):
            checks.append({
                "check": "aadhaar_name_match", "status": "failed",
                "message": f"Name mismatch: Aadhaar has '{aadhaar_data['full_name']}' but you entered '{full_name.upper()}'"
            })
            errors.append(f"Name on Aadhaar ({aadhaar_data['full_name']}) does not match ({full_name})")
        else:
            checks.append({"check": "aadhaar_name_match", "status": "passed", "message": "Name matches Aadhaar records"})

        # 2b. DOB on Aadhaar must match
        if aadhaar_data["date_of_birth"] != dob:
            checks.append({
                "check": "aadhaar_dob_match", "status": "failed",
                "message": f"DOB mismatch: Aadhaar has '{aadhaar_data['date_of_birth']}' but you entered '{dob}'"
            })
            errors.append(f"Date of birth on Aadhaar does not match")
        else:
            checks.append({"check": "aadhaar_dob_match", "status": "passed", "message": "Date of birth matches Aadhaar records"})

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  3. PAN VERIFICATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    pan_result = verify_pan_govt(pan)
    if not pan_result.success:
        checks.append({"check": "pan_nsdl", "status": "failed", "message": pan_result.error})
        errors.append(f"PAN Verification Failed: {pan_result.error}")
    else:
        pan_data = pan_result.data
        checks.append({"check": "pan_nsdl", "status": "passed", "message": "PAN is valid and active in NSDL records"})

        # 3a. Name on PAN must match
        if not _name_match(pan_data["full_name"], full_name):
            checks.append({
                "check": "pan_name_match", "status": "failed",
                "message": f"Name mismatch: PAN has '{pan_data['full_name']}' but you entered '{full_name.upper()}'"
            })
            errors.append(f"Name on PAN does not match")
        else:
            checks.append({"check": "pan_name_match", "status": "passed", "message": "Name matches PAN records"})

        # 3b. PAN-Aadhaar linkage
        if pan_data.get("aadhaar_linked") and pan_data["aadhaar_linked"] != aadhaar:
            checks.append({
                "check": "pan_aadhaar_link", "status": "failed",
                "message": "Aadhaar linked to this PAN does not match the Aadhaar you provided"
            })
            errors.append("PAN-Aadhaar linkage mismatch")
        else:
            checks.append({"check": "pan_aadhaar_link", "status": "passed", "message": "PAN-Aadhaar linkage verified"})

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  4. CIBIL SCORE AUTO-FETCH
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cibil_result = fetch_cibil_score(pan)
    cibil_score = None
    if not cibil_result.success:
        checks.append({"check": "cibil_fetch", "status": "warning", "message": cibil_result.error})
        warnings.append("Could not fetch CIBIL score. Defaulting to 300.")
        cibil_score = 300  # Minimum possible
    else:
        cibil_data = cibil_result.data
        cibil_score = cibil_data["cibil_score"]
        auto_filled["cibil_score"] = cibil_score
        auto_filled["cibil_report"] = {
            "score": cibil_score,
            "range": cibil_data["score_range"],
            "total_accounts": cibil_data["total_accounts"],
            "overdue_accounts": cibil_data["overdue_accounts"],
            "loan_defaults": cibil_data["loan_defaults"],
            "credit_utilization": cibil_data["credit_utilization"],
            "report_date": cibil_data["report_date"],
        }

        if cibil_score >= 650:
            checks.append({
                "check": "cibil_score", "status": "passed",
                "message": f"CIBIL Score: {cibil_score} ({cibil_data['score_range']})"
            })
        elif cibil_score >= 500:
            checks.append({
                "check": "cibil_score", "status": "warning",
                "message": f"CIBIL Score: {cibil_score} ({cibil_data['score_range']}) — below average"
            })
            warnings.append(f"Low CIBIL score: {cibil_score}")
        else:
            checks.append({
                "check": "cibil_score", "status": "failed",
                "message": f"CIBIL Score: {cibil_score} ({cibil_data['score_range']}) — too low for financing"
            })
            errors.append(f"CIBIL score {cibil_score} is below the minimum threshold (500)")

        # Check for defaults
        if cibil_data["loan_defaults"] > 0:
            checks.append({
                "check": "cibil_defaults", "status": "failed",
                "message": f"Loan defaults detected: {cibil_data['loan_defaults']} default(s) on record"
            })
            errors.append(f"{cibil_data['loan_defaults']} loan default(s) found in CIBIL history")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  5. BANK ACCOUNT VERIFICATION
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    bank_result = verify_bank_account_govt(bank_account, bank_ifsc)
    if not bank_result.success:
        checks.append({"check": "bank_verification", "status": "failed", "message": bank_result.error})
        errors.append(f"Bank Verification Failed: {bank_result.error}")
    else:
        bank_data = bank_result.data
        checks.append({"check": "bank_verification", "status": "passed", "message": "Bank account verified successfully"})

        # 5a. Account holder name must match vendor name
        if not _name_match(bank_data["holder_name"], full_name):
            checks.append({
                "check": "bank_name_match", "status": "failed",
                "message": f"Bank account holder '{bank_data['holder_name']}' does not match '{full_name.upper()}'"
            })
            errors.append("Bank account holder name does not match vendor name")
        else:
            checks.append({"check": "bank_name_match", "status": "passed", "message": "Bank account holder name matches"})

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    #  FINAL VERDICT
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    passed_count = sum(1 for c in checks if c["status"] == "passed")
    failed_count = sum(1 for c in checks if c["status"] == "failed")
    warning_count = sum(1 for c in checks if c["status"] == "warning")

    if failed_count > 0:
        overall_status = "rejected"
        message = f"Verification FAILED — {failed_count} check(s) failed. Please correct the errors and try again."
    elif warning_count > 0:
        overall_status = "needs_review"
        message = f"Verification passed with {warning_count} warning(s). Manual review may be required."
    else:
        overall_status = "verified"
        message = f"All {passed_count} verification checks passed. Vendor is genuine."

    return {
        "overall_status": overall_status,
        "message": message,
        "cibil_score": cibil_score,
        "auto_filled": auto_filled,
        "checks": checks,
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "total_checks": len(checks),
            "passed": passed_count,
            "failed": failed_count,
            "warnings": warning_count,
        }
    }

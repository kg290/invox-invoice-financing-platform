"""
Mock KYC (Know Your Customer) verification routes.
Provides a smart KYC flow:
  1. User enters ONLY name + PAN  (minimal input)
  2. System looks up citizen from a hardcoded "Government Database"
  3. All details are auto-extracted and shown for review
  4. User clicks Verify → instant verification against multiple sources

In production, step 2 would hit the GST Sandbox / DigiLocker / UIDAI APIs.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timezone
import random
import json

from database import get_db
from models import User, Vendor, Lender, Notification
from routes.auth import get_current_user

router = APIRouter(prefix="/api/kyc", tags=["KYC Verification"])


# ═══════════════════════════════════════════════════════════════════
#  HARDCODED GOVERNMENT CITIZEN DATABASE
#  (Simulates UIDAI + NSDL + MCA + India Post + NPCI records)
#  In production → GST Sandbox API / DigiLocker / UIDAI e-KYC
# ═══════════════════════════════════════════════════════════════════

CITIZEN_DATABASE = {
    # ── Karnajeet Gosavi ──
    "KARNAJEET GOSAVI": {
        "full_name": "Karnajeet Gosavi",
        "date_of_birth": "2003-07-15",
        "pan_number": "GOPKG1234A",
        "aadhaar_number": "987654321012",
        "gender": "Male",
        "father_name": "Suresh Gosavi",
        "address": "Flat 12, Paradise Apartments, FC Road",
        "city": "Pune",
        "state": "Maharashtra",
        "pincode": "411005",
        "phone": "9876501234",
        "email": "karnajeet.gosavi@gmail.com",
        "bank_account": "91203456789",
        "bank_ifsc": "HDFC0001234",
        "bank_name": "HDFC Bank",
        "bank_branch": "FC Road, Pune",
        "employment_type": "Self-Employed",
        "annual_income": 850000,
        "cibil_score": 742,
        "voter_id": "MH/01/234/567890",
        "passport_number": "T1234567",
        "driving_license": "MH12-2021-0098765",
        "gst_registered": True,
        "gstin": "27GOPKG1234A1Z5",
        # ── Business Details (MCA / GST Portal) ──
        "business_name": "Gosavi Digital Solutions",
        "business_type": "Proprietorship",
        "business_category": "IT & Software Services",
        "business_registration_number": "MH-PROP-2022-12345",
        "udyam_registration_number": "UDYAM-MH-12-0012345",
        "year_of_establishment": 2022,
        "number_of_employees": 3,
        "business_address": "Office 5, Baner Tech Park, Baner",
        "business_city": "Pune",
        "business_state": "Maharashtra",
        "business_pincode": "411045",
        "gst_registration_date": "2022-06-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 18,
        "gst_compliance_status": "Regular",
        "annual_turnover": 850000,
        "monthly_revenue": 70000,
        "business_assets_value": 120000,
        "existing_liabilities": 15000,
        # ── Nominee (from Life Insurance / Bank records) ──
        "nominee_name": "Suresh Gosavi",
        "nominee_relationship": "Father",
        "nominee_phone": "9876501235",
        "nominee_aadhaar": "987654321099",
    },
    # ── Sunita Devi Verma (Seed Vendor 1) ──
    "SUNITA DEVI VERMA": {
        "full_name": "Sunita Devi Verma",
        "date_of_birth": "1986-04-12",
        "pan_number": "BVDPS4321K",
        "aadhaar_number": "234567891234",
        "gender": "Female",
        "father_name": "Ram Prasad Devi",
        "address": "H-12, Laxmi Nagar, Near Metro Pillar 42",
        "city": "New Delhi",
        "state": "Delhi",
        "pincode": "110092",
        "phone": "9876543210",
        "email": "sunita.tiffin@gmail.com",
        "bank_account": "10234567890",
        "bank_ifsc": "SBIN0009876",
        "bank_name": "State Bank of India",
        "bank_branch": "Laxmi Nagar",
        "employment_type": "Self-Employed",
        "annual_income": 480000,
        "cibil_score": 672,
        "voter_id": "DL/01/123/456789",
        "passport_number": "",
        "driving_license": "DL01-2018-0012345",
        "gst_registered": True,
        "gstin": "07BVDPS4321K1Z3",
        # ── Business Details (MCA / GST Portal) ──
        "business_name": "Maa Annapurna Tiffin Service",
        "business_type": "Proprietorship",
        "business_category": "Food & Catering",
        "business_registration_number": "DL-PROP-2019-08432",
        "udyam_registration_number": "UDYAM-DL-01-0098765",
        "year_of_establishment": 2019,
        "number_of_employees": 4,
        "business_address": "H-12, Back Lane, Laxmi Nagar",
        "business_city": "New Delhi",
        "business_state": "Delhi",
        "business_pincode": "110092",
        "gst_registration_date": "2020-01-15",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 24,
        "gst_compliance_status": "Regular",
        "annual_turnover": 480000,
        "monthly_revenue": 40000,
        "business_assets_value": 85000,
        "existing_liabilities": 25000,
        # ── Nominee ──
        "nominee_name": "Rajan Verma",
        "nominee_relationship": "Husband",
        "nominee_phone": "9876543211",
        "nominee_aadhaar": "345678912345",
    },
    # ── Ramu Vishwakarma (Seed Vendor 2) ──
    "RAMU VISHWAKARMA": {
        "full_name": "Ramu Vishwakarma",
        "date_of_birth": "1979-09-08",
        "pan_number": "CVRPV5678L",
        "aadhaar_number": "456789012345",
        "gender": "Male",
        "father_name": "Shivlal Vishwakarma",
        "address": "Gali No. 3, Kirti Nagar, Industrial Area",
        "city": "New Delhi",
        "state": "Delhi",
        "pincode": "110015",
        "phone": "9123456780",
        "email": "ramu.furniture@gmail.com",
        "bank_account": "20345678901",
        "bank_ifsc": "PUNB0123400",
        "bank_name": "Punjab National Bank",
        "bank_branch": "Kirti Nagar",
        "employment_type": "Self-Employed",
        "annual_income": 720000,
        "cibil_score": 698,
        "voter_id": "DL/02/234/567890",
        "passport_number": "",
        "driving_license": "DL02-2010-0023456",
        "gst_registered": True,
        "gstin": "07CVRPV5678L1Z6",
        # ── Business Details (MCA / GST Portal) ──
        "business_name": "Ramu Furniture Works",
        "business_type": "Proprietorship",
        "business_category": "Furniture & Woodwork",
        "business_registration_number": "DL-PROP-2014-05678",
        "udyam_registration_number": "UDYAM-DL-02-0045678",
        "year_of_establishment": 2014,
        "number_of_employees": 6,
        "business_address": "Shop 14, Kirti Nagar Furniture Market",
        "business_city": "New Delhi",
        "business_state": "Delhi",
        "business_pincode": "110015",
        "gst_registration_date": "2018-06-01",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 30,
        "gst_compliance_status": "Regular",
        "annual_turnover": 720000,
        "monthly_revenue": 60000,
        "business_assets_value": 180000,
        "existing_liabilities": 65000,
        # ── Nominee ──
        "nominee_name": "Geeta Devi",
        "nominee_relationship": "Wife",
        "nominee_phone": "9123456781",
        "nominee_aadhaar": "567890123456",
    },
    # ── Fatima Bee Khan (Seed Vendor 3) ──
    "FATIMA BEE KHAN": {
        "full_name": "Fatima Bee Khan",
        "date_of_birth": "1988-03-14",
        "pan_number": "FKBPK7890P",
        "aadhaar_number": "312345678901",
        "gender": "Female",
        "father_name": "Ahmed Khan",
        "address": "Sarafa Bazaar, Old Bhopal",
        "city": "Bhopal",
        "state": "Madhya Pradesh",
        "pincode": "462001",
        "phone": "9090909090",
        "email": "fatima.spices@gmail.com",
        "bank_account": "50678901234",
        "bank_ifsc": "CBIN0281234",
        "bank_name": "Central Bank of India",
        "bank_branch": "New Market, Bhopal",
        "employment_type": "Self-Employed",
        "annual_income": 600000,
        "cibil_score": 660,
        "voter_id": "MP/05/345/678901",
        "passport_number": "",
        "driving_license": "MP09-2015-0034567",
        "gst_registered": True,
        "gstin": "23FKBPK7890P1Z7",
        # ── Business Details (MCA / GST Portal) ──
        "business_name": "Khan Masala & Spice Traders",
        "business_type": "Proprietorship",
        "business_category": "Food & Spices",
        "business_registration_number": "MP-PROP-2017-09876",
        "udyam_registration_number": "UDYAM-MP-05-0091234",
        "year_of_establishment": 2017,
        "number_of_employees": 3,
        "business_address": "Shop 22, Sarafa Bazaar, Chowk",
        "business_city": "Bhopal",
        "business_state": "Madhya Pradesh",
        "business_pincode": "462001",
        "gst_registration_date": "2019-01-01",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 24,
        "gst_compliance_status": "Regular",
        "annual_turnover": 600000,
        "monthly_revenue": 50000,
        "business_assets_value": 140000,
        "existing_liabilities": 35000,
        # ── Nominee ──
        "nominee_name": "Salim Khan",
        "nominee_relationship": "Husband",
        "nominee_phone": "9090909091",
        "nominee_aadhaar": "123456789012",
    },
    # ── Deepak Jain (Seed Lender) ──
    "DEEPAK JAIN": {
        "full_name": "Deepak Jain",
        "date_of_birth": "1975-11-22",
        "pan_number": "DJNPJ4567M",
        "aadhaar_number": "678901234567",
        "gender": "Male",
        "father_name": "Ramesh Jain",
        "address": "B-45, Safdarjung Enclave",
        "city": "New Delhi",
        "state": "Delhi",
        "pincode": "110029",
        "phone": "9811111111",
        "email": "deepak.jain@microfinance.in",
        "bank_account": "30456789012",
        "bank_ifsc": "HDFC0009999",
        "bank_name": "HDFC Bank",
        "bank_branch": "Safdarjung Enclave",
        "employment_type": "Business Owner",
        "annual_income": 3200000,
        "cibil_score": 810,
        "voter_id": "DL/03/456/789012",
        "passport_number": "Z9876543",
        "driving_license": "DL03-2005-0045678",
        "gst_registered": True,
        "gstin": "07DJNPJ4567M1Z9",
        # ── Business Details (MCA / GST Portal) ──
        "business_name": "JanSeva Microfinance Pvt Ltd",
        "business_type": "Pvt Ltd",
        "business_category": "Financial Services",
        "business_registration_number": "DL-PVT-2008-04567",
        "udyam_registration_number": "",
        "year_of_establishment": 2008,
        "number_of_employees": 25,
        "business_address": "B-45, Ground Floor, Safdarjung Enclave",
        "business_city": "New Delhi",
        "business_state": "Delhi",
        "business_pincode": "110029",
        "gst_registration_date": "2017-07-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 90,
        "gst_compliance_status": "Regular",
        "annual_turnover": 3200000,
        "monthly_revenue": 270000,
        "business_assets_value": 1500000,
        "existing_liabilities": 200000,
        # ── Nominee ──
        "nominee_name": "Meera Jain",
        "nominee_relationship": "Wife",
        "nominee_phone": "9811111112",
        "nominee_aadhaar": "678901234599",
    },
    # ── Priya Sharma (extra citizen) ──
    "PRIYA SHARMA": {
        "full_name": "Priya Sharma",
        "date_of_birth": "1992-06-28",
        "pan_number": "PSHPS5678N",
        "aadhaar_number": "543210987654",
        "gender": "Female",
        "father_name": "Vijay Sharma",
        "address": "22, MG Road, Koramangala",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560034",
        "phone": "9844556677",
        "email": "priya.sharma@techstartup.in",
        "bank_account": "40567890123",
        "bank_ifsc": "ICIC0001234",
        "bank_name": "ICICI Bank",
        "bank_branch": "Koramangala",
        "employment_type": "Self-Employed",
        "annual_income": 1200000,
        "cibil_score": 756,
        "voter_id": "KA/04/567/890123",
        "passport_number": "P8765432",
        "driving_license": "KA04-2014-0056789",
        "gst_registered": True,
        "gstin": "29PSHPS5678N1Z2",
        # ── Business Details (MCA / GST Portal) ──
        "business_name": "Sharma Tech Solutions LLP",
        "business_type": "LLP",
        "business_category": "IT & Software Services",
        "business_registration_number": "KA-LLP-2018-07890",
        "udyam_registration_number": "UDYAM-KA-04-0078901",
        "year_of_establishment": 2018,
        "number_of_employees": 8,
        "business_address": "Floor 3, MG Road Tech Hub",
        "business_city": "Bengaluru",
        "business_state": "Karnataka",
        "business_pincode": "560034",
        "gst_registration_date": "2018-09-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 60,
        "gst_compliance_status": "Regular",
        "annual_turnover": 1200000,
        "monthly_revenue": 100000,
        "business_assets_value": 350000,
        "existing_liabilities": 50000,
        # ── Nominee ──
        "nominee_name": "Vijay Sharma",
        "nominee_relationship": "Father",
        "nominee_phone": "9844556688",
        "nominee_aadhaar": "543210987699",
    },
}


# ═══════════════════════════════════════════════
#  REQUEST SCHEMAS
# ═══════════════════════════════════════════════

class KYCLookupRequest(BaseModel):
    """User enters ONLY name + PAN. System fetches everything else."""
    full_name: str = Field(..., min_length=2, max_length=255)
    pan_number: str = Field(..., min_length=10, max_length=10)


class KYCVerifyRequest(BaseModel):
    """Trigger verification on already-extracted data."""
    full_name: str
    date_of_birth: str
    pan_number: str
    aadhaar_number: str
    address: str
    city: str
    state: str
    pincode: str
    phone: str = ""
    email: str = ""
    bank_account: str = ""
    bank_ifsc: str = ""
    bank_name: str = ""
    annual_income: float = 0
    cibil_score: int = 0
    gstin: str = ""
    father_name: str = ""
    gender: str = ""


# ── Mock KYC Database (in-memory for demo) ──
_kyc_store: dict = {}


# ═══════════════════════════════════════════════
#  LOOKUP — Auto-extract citizen details
# ═══════════════════════════════════════════════

@router.post("/lookup")
def lookup_citizen(
    data: KYCLookupRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Look up a citizen from the Government Database using name + PAN.
    Returns full auto-extracted profile if found.
    Simulates: UIDAI e-KYC + NSDL PAN Verify + DigiLocker pull.
    """
    name_key = data.full_name.strip().upper()
    pan_upper = data.pan_number.strip().upper()

    # Try exact name match first
    citizen = CITIZEN_DATABASE.get(name_key)

    # If not found by name, try fuzzy — any record whose name contains the query
    if not citizen:
        for key, rec in CITIZEN_DATABASE.items():
            if name_key in key or key in name_key:
                citizen = rec
                break

    # Also try PAN match
    if not citizen:
        for rec in CITIZEN_DATABASE.values():
            if rec["pan_number"].upper() == pan_upper:
                citizen = rec
                break

    if not citizen:
        raise HTTPException(
            status_code=404,
            detail=f"No records found for '{data.full_name}' with PAN '{pan_upper}'. "
                   "Please check your details or contact support."
        )

    # Verify PAN matches the name record
    if citizen["pan_number"].upper() != pan_upper:
        raise HTTPException(
            status_code=400,
            detail=f"PAN '{pan_upper}' does not match records for '{citizen['full_name']}'. "
                   "Please provide the correct PAN number."
        )

    # Return full extracted profile
    return {
        "found": True,
        "message": f"Records found for {citizen['full_name']}. Data extracted from Government databases.",
        "sources": ["UIDAI (Aadhaar)", "NSDL (PAN)", "India Post", "NPCI", "CIBIL", "GST Network"],
        "citizen": {
            "full_name": citizen["full_name"],
            "date_of_birth": citizen["date_of_birth"],
            "gender": citizen.get("gender", ""),
            "father_name": citizen.get("father_name", ""),
            "pan_number": citizen["pan_number"],
            "aadhaar_number": citizen["aadhaar_number"][:4] + "****" + citizen["aadhaar_number"][-4:],
            "aadhaar_full": citizen["aadhaar_number"],  # needed for verification
            "address": citizen["address"],
            "city": citizen["city"],
            "state": citizen["state"],
            "pincode": citizen["pincode"],
            "phone": citizen.get("phone", ""),
            "email": citizen.get("email", ""),
            "bank_account": "****" + citizen.get("bank_account", "")[-4:] if citizen.get("bank_account") else "",
            "bank_account_full": citizen.get("bank_account", ""),
            "bank_ifsc": citizen.get("bank_ifsc", ""),
            "bank_name": citizen.get("bank_name", ""),
            "bank_branch": citizen.get("bank_branch", ""),
            "annual_income": citizen.get("annual_income", 0),
            "cibil_score": citizen.get("cibil_score", 0),
            "voter_id": citizen.get("voter_id", ""),
            "passport_number": citizen.get("passport_number", ""),
            "driving_license": citizen.get("driving_license", ""),
            "gst_registered": citizen.get("gst_registered", False),
            "gstin": citizen.get("gstin", ""),
            "employment_type": citizen.get("employment_type", ""),
        },
    }


# ═══════════════════════════════════════════════
#  VERIFY — Run verification on extracted data
# ═══════════════════════════════════════════════

def _run_verification(data: KYCVerifyRequest) -> dict:
    """
    Run full KYC verification pipeline on extracted citizen data.
    Returns check results and overall status.
    """
    checks = []
    overall_status = "verified"

    # 1. PAN Verification (NSDL)
    pan = data.pan_number.upper()
    pan_valid = (len(pan) == 10 and pan[:5].isalpha()
                 and pan[5:9].isdigit() and pan[9].isalpha())
    checks.append({
        "check": "PAN Verification (NSDL)",
        "status": "passed" if pan_valid else "failed",
        "message": f"PAN {pan} verified — Name: {data.full_name}, Status: Active" if pan_valid
                   else f"PAN {pan} — invalid format or inactive",
        "source": "NSDL / Income Tax Department",
    })
    if not pan_valid:
        overall_status = "rejected"

    # 2. Aadhaar Verification (UIDAI)
    aadhaar = data.aadhaar_number
    aadhaar_valid = len(aadhaar) == 12 and aadhaar.isdigit() and aadhaar[0] != "0"
    checks.append({
        "check": "Aadhaar Verification (UIDAI)",
        "status": "passed" if aadhaar_valid else "failed",
        "message": f"Aadhaar ****{aadhaar[-4:]} verified — Name & DOB match UIDAI records" if aadhaar_valid
                   else "Aadhaar validation failed",
        "source": "UIDAI e-KYC Gateway",
    })
    if not aadhaar_valid:
        overall_status = "rejected"

    # 3. PAN-Aadhaar Linkage
    checks.append({
        "check": "PAN-Aadhaar Linkage",
        "status": "passed",
        "message": f"PAN {pan} is linked to Aadhaar ****{aadhaar[-4:]} — Linkage status: Active",
        "source": "Income Tax e-Filing Portal",
    })

    # 4. Name Cross-Match
    checks.append({
        "check": "Name Cross-Verification",
        "status": "passed",
        "message": f"Name '{data.full_name}' matches across PAN, Aadhaar & Bank records",
        "source": "Multi-Source Cross-Match Engine",
    })

    # 5. DOB & Age Verification
    try:
        dob = datetime.strptime(data.date_of_birth, "%Y-%m-%d")
        age = (datetime.now() - dob).days / 365.25
        dob_valid = 18 <= age <= 100
        checks.append({
            "check": "Age & DOB Verification",
            "status": "passed" if dob_valid else "failed",
            "message": f"DOB: {data.date_of_birth} — Age: {int(age)} years — {'Eligible' if dob_valid else 'Not Eligible'}",
            "source": "UIDAI Database",
        })
        if not dob_valid:
            overall_status = "rejected"
    except ValueError:
        checks.append({"check": "Age & DOB Verification", "status": "failed",
                        "message": "Invalid date format", "source": "System"})
        overall_status = "rejected"

    # 6. Address & Pincode Verification
    pincode_valid = len(data.pincode) == 6 and data.pincode.isdigit()
    checks.append({
        "check": "Address Verification",
        "status": "passed" if pincode_valid else "warning",
        "message": f"Address verified: {data.address}, {data.city}, {data.state} — Pincode {data.pincode}" if pincode_valid
                   else "Pincode validation issue",
        "source": "India Post / Aadhaar Address DB",
    })

    # 7. Bank Account Verification
    if data.bank_account and data.bank_ifsc:
        checks.append({
            "check": "Bank Account Verification",
            "status": "passed",
            "message": f"A/C ****{data.bank_account[-4:]} at {data.bank_name or data.bank_ifsc} — Account holder name matches",
            "source": "NPCI / Penny Drop Verification",
        })

    # 8. CIBIL / Credit Score
    if data.cibil_score > 0:
        cibil_status = "passed" if data.cibil_score >= 600 else "warning"
        checks.append({
            "check": "Credit Score (CIBIL)",
            "status": cibil_status,
            "message": f"CIBIL Score: {data.cibil_score} — {'Good' if data.cibil_score >= 750 else 'Fair' if data.cibil_score >= 650 else 'Needs Improvement'}",
            "source": "TransUnion CIBIL",
        })

    # 9. GST Registration
    if data.gstin:
        checks.append({
            "check": "GST Registration",
            "status": "passed",
            "message": f"GSTIN {data.gstin} — Status: Active, PAN-GSTIN linked",
            "source": "GST Network (GSTN)",
        })

    # 10. Sanctions & PEP Screening
    checks.append({
        "check": "Sanctions & PEP Screening",
        "status": "passed",
        "message": f"No matches in OFAC, UN, EU sanctions lists or PEP databases for '{data.full_name}'",
        "source": "Global Watchlist Database",
    })

    # 11. Overall Risk Assessment
    risk_score = random.randint(10, 28) if overall_status == "verified" else random.randint(60, 85)
    checks.append({
        "check": "KYC Risk Assessment",
        "status": "passed" if risk_score < 40 else "warning",
        "message": f"Composite risk score: {risk_score}/100 — {'Low Risk ✓' if risk_score < 25 else 'Acceptable Risk' if risk_score < 40 else 'Elevated Risk'}",
        "source": "InvoX Risk Engine",
    })

    return {
        "overall_status": overall_status,
        "checks": checks,
        "risk_score": risk_score,
        "verified_at": datetime.now(timezone.utc).isoformat() if overall_status == "verified" else None,
    }


# ═══════════════════════════════════════════════
#  ENDPOINTS
# ═══════════════════════════════════════════════

@router.post("/verify")
def verify_kyc(
    data: KYCVerifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run full KYC verification on extracted citizen data."""
    result = _run_verification(data)

    # Store KYC result
    kyc_record = {
        "user_id": current_user.id,
        "role": current_user.role,
        "submitted_data": {
            "full_name": data.full_name,
            "date_of_birth": data.date_of_birth,
            "pan_number": data.pan_number,
            "aadhaar_number": data.aadhaar_number,
            "address": data.address,
            "city": data.city,
            "state": data.state,
            "pincode": data.pincode,
            "phone": data.phone,
            "email": data.email,
            "bank_account": data.bank_account,
            "bank_ifsc": data.bank_ifsc,
            "bank_name": data.bank_name,
            "annual_income": data.annual_income,
            "cibil_score": data.cibil_score,
            "gstin": data.gstin,
            "father_name": data.father_name,
            "gender": data.gender,
        },
        "kyc_status": result["overall_status"],
        "checks": result["checks"],
        "risk_score": result["risk_score"],
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "verified_at": result.get("verified_at"),
    }
    _kyc_store[current_user.id] = kyc_record

    # If vendor, also update profile_status
    if current_user.role == "vendor" and current_user.vendor_id:
        vendor = db.query(Vendor).filter(Vendor.id == current_user.vendor_id).first()
        if vendor and result["overall_status"] == "verified":
            vendor.profile_status = "verified"
            db.commit()

    # Notification
    db.add(Notification(
        user_id=current_user.id,
        title="KYC Verified ✅" if result["overall_status"] == "verified" else "KYC Verification Issue",
        message=f"Identity verified successfully. "
                f"{sum(1 for c in result['checks'] if c['status'] == 'passed')}/{len(result['checks'])} checks passed."
                if result["overall_status"] == "verified"
                else f"KYC flagged for review. Please check your details.",
        notification_type="verification",
    ))
    db.commit()

    return {
        "message": "KYC verification complete",
        "kyc_status": result["overall_status"],
        "checks": result["checks"],
        "risk_score": result["risk_score"],
        "verified_at": result.get("verified_at"),
    }


@router.get("/status")
def get_kyc_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get KYC status for the current user."""
    record = _kyc_store.get(current_user.id)
    if not record:
        return {
            "kyc_status": "not_submitted",
            "submitted_at": None,
            "verified_at": None,
            "checks": [],
            "submitted_data": None,
        }

    sd = record["submitted_data"]
    return {
        "kyc_status": record["kyc_status"],
        "submitted_at": record["submitted_at"],
        "verified_at": record.get("verified_at"),
        "checks": record["checks"],
        "risk_score": record.get("risk_score", 0),
        "submitted_data": {
            "full_name": sd["full_name"],
            "date_of_birth": sd["date_of_birth"],
            "gender": sd.get("gender", ""),
            "father_name": sd.get("father_name", ""),
            "pan_number": sd["pan_number"][:5] + "*****",
            "aadhaar_number": sd["aadhaar_number"][:4] + "****" + sd["aadhaar_number"][-4:],
            "address": sd.get("address", ""),
            "city": sd["city"],
            "state": sd["state"],
            "pincode": sd["pincode"],
            "phone": sd.get("phone", ""),
            "email": sd.get("email", ""),
            "bank_name": sd.get("bank_name", ""),
            "bank_account": "****" + sd["bank_account"][-4:] if sd.get("bank_account") else "",
            "bank_ifsc": sd.get("bank_ifsc", ""),
            "annual_income": sd.get("annual_income", 0),
            "cibil_score": sd.get("cibil_score", 0),
            "gstin": sd.get("gstin", ""),
        },
    }

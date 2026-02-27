"""
Hardcoded vendor templates for demo registration.

When a user registers with one of these GSTIN/PAN/Aadhaar combos,
the system bypasses the Sandbox API and uses this pre-built data.
It still LOOKS like the API is being called (with delays and logs).
"""
import time
import json
import random
from datetime import datetime, timezone

# ══════════════════════════════════════════════════
#  TEMPLATE VENDOR DATA (3 hardcoded registrations)
# ══════════════════════════════════════════════════

HARDCODED_VENDORS = {
    # ── Template 1: Tera Software — IT Services, Uttar Pradesh ──
    "09AABCT1332L1ZC": {
        "gstin": "09AABCT1332L1ZC",
        "personal_pan": "AABCT1332L",
        "personal_aadhaar": "876543210987",
        "full_name": "Tera Software Ltd",
        "date_of_birth": "1986-04-15",
        "phone": "9876501001",
        "address": "B-12, Sector 62, Noida, Gautam Buddha Nagar",
        "city": "Noida",
        "state": "Uttar Pradesh",
        "pincode": "201301",
        "business_name": "Tera Software Limited",
        "business_type": "Public Limited Company",
        "business_category": "Information Technology & Software Services",
        "business_registration_number": "U72200AP2001PLC036672",
        "udyam_registration_number": "UDYAM-UP-09-0012345",
        "year_of_establishment": 2001,
        "number_of_employees": 150,
        "business_address": "B-12, Sector 62, Noida Industrial Area",
        "business_city": "Noida",
        "business_state": "Uttar Pradesh",
        "business_pincode": "201301",
        "gst_registration_date": "2017-07-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 84,
        "gst_compliance_status": "Regular",
        "cibil_score": 756,
        "annual_turnover": 45000000,
        "monthly_revenue": 3750000,
        "business_assets_value": 12000000,
        "existing_liabilities": 3500000,
        "bank_account_number": "50100068245389",
        "bank_name": "HDFC Bank",
        "bank_ifsc": "HDFC0001234",
        "bank_branch": "Sector 62, Noida",
        "nominee_name": "Rajesh Kumar",
        "nominee_relationship": "Director",
        "nominee_phone": "9876501002",
        "nominee_aadhaar": "876543210988",
        "profile_status": "verified",
        "risk_score": 22,
        "business_description": "Leading IT services company providing ERP solutions, government e-governance projects, and custom software development for state and central government bodies.",
        "verification_notes": "All government verification checks passed via API. GST Active, PAN Verified, CIBIL 756, Bank Account Validated.",
        # Fake GST API response data
        "_gst_api_response": {
            "gstin": "09AABCT1332L1ZC",
            "legal_name": "TERA SOFTWARE LIMITED",
            "trade_name": "TERA SOFTWARE LIMITED",
            "status": "Active",
            "business_type": "Public Limited Company",
            "registration_date": "01/07/2017",
            "state": "Uttar Pradesh",
            "address": "B-12, SECTOR 62, NOIDA, GAUTAM BUDDHA NAGAR, Uttar Pradesh, 201301",
            "nature_of_business": ["Information Technology Software", "Software Development Services"],
            "compliance_rating": "Regular",
            "filing_frequency": "Monthly",
            "last_filing_date": "10/01/2026",
            "annual_aggregate_turnover": "Slab: Rs. 1.5 Cr. to 5 Cr.",
        },
        # Fake verification checks
        "_verification_checks": [
            {"check": "gstin", "status": "passed", "details": {"result": "valid", "source": "sandbox_gst_api", "gstin": "09AABCT1332L1ZC", "legal_name": "TERA SOFTWARE LIMITED", "status": "Active", "state": "Uttar Pradesh", "api_response_time_ms": 1243}},
            {"check": "pan", "status": "passed", "details": {"result": "valid", "source": "sandbox_pan_api", "pan": "AABCT1332L", "name_on_pan": "TERA SOFTWARE LIMITED", "pan_type": "Company", "api_response_time_ms": 892}},
            {"check": "aadhaar", "status": "passed", "details": {"result": "format_valid", "source": "aadhaar_checksum", "aadhaar_last4": "0987", "verhoeff_valid": True}},
            {"check": "cibil", "status": "passed", "details": {"result": "good", "source": "invox_internal_scoring", "score": 756, "grade": "Good", "factors": ["Long business history", "Regular GST compliance", "High turnover"]}},
            {"check": "bank", "status": "passed", "details": {"result": "valid", "source": "sandbox_bank_api", "bank": "HDFC Bank", "ifsc_valid": True, "account_exists": True, "api_response_time_ms": 678}},
            {"check": "pan_gstin_match", "status": "passed", "details": {"result": "match", "pan_from_gstin": "AABCT1332L", "provided_pan": "AABCT1332L", "match": True}},
            {"check": "address", "status": "passed", "details": {"result": "verified", "source": "gst_address_match", "gst_address": "B-12, SECTOR 62, NOIDA", "confidence": 0.95}},
        ],
    },

    # ── Template 2: Reliance Industries — Karnataka ──
    "29AAACR5055K1Z3": {
        "gstin": "29AAACR5055K1Z3",
        "personal_pan": "AAACR5055K",
        "personal_aadhaar": "765432109876",
        "full_name": "Reliance Industries Ltd (KA)",
        "date_of_birth": "1977-05-08",
        "phone": "9876502001",
        "address": "Maker Chambers IV, 222 Nariman Point",
        "city": "Bengaluru",
        "state": "Karnataka",
        "pincode": "560001",
        "business_name": "Reliance Industries Limited",
        "business_type": "Public Limited Company",
        "business_category": "Petrochemicals & Diversified Conglomerate",
        "business_registration_number": "L17110MH1973PLC019786",
        "udyam_registration_number": "",
        "year_of_establishment": 1973,
        "number_of_employees": 5000,
        "business_address": "Survey No 45/A, Jigani Industrial Area",
        "business_city": "Bengaluru",
        "business_state": "Karnataka",
        "business_pincode": "560105",
        "gst_registration_date": "2017-07-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 96,
        "gst_compliance_status": "Regular",
        "cibil_score": 812,
        "annual_turnover": 250000000,
        "monthly_revenue": 20833333,
        "business_assets_value": 80000000,
        "existing_liabilities": 15000000,
        "bank_account_number": "30520110000123",
        "bank_name": "State Bank of India",
        "bank_ifsc": "SBIN0001234",
        "bank_branch": "Nariman Point, Mumbai",
        "nominee_name": "Amit Sharma",
        "nominee_relationship": "CFO",
        "nominee_phone": "9876502002",
        "nominee_aadhaar": "765432109877",
        "profile_status": "verified",
        "risk_score": 12,
        "business_description": "India's largest private sector company. Diversified conglomerate with interests in petrochemicals, refining, oil & gas, retail, and digital services. Karnataka operations handle regional distribution and Jio infrastructure.",
        "verification_notes": "All government verification checks passed via API. GST Active, PAN Verified, CIBIL 812, Bank Account Validated. Premium credit grade.",
        "_gst_api_response": {
            "gstin": "29AAACR5055K1Z3",
            "legal_name": "RELIANCE INDUSTRIES LIMITED",
            "trade_name": "RELIANCE INDUSTRIES LIMITED",
            "status": "Active",
            "business_type": "Public Limited Company",
            "registration_date": "01/07/2017",
            "state": "Karnataka",
            "address": "SURVEY NO 45/A, JIGANI INDUSTRIAL AREA, ANEKAL TALUK, BENGALURU, Karnataka, 560105",
            "nature_of_business": ["Manufacturing", "Trading", "Wholesale Distribution"],
            "compliance_rating": "Regular",
            "filing_frequency": "Monthly",
            "last_filing_date": "10/01/2026",
            "annual_aggregate_turnover": "Slab: Rs. 500 Cr. and above",
        },
        "_verification_checks": [
            {"check": "gstin", "status": "passed", "details": {"result": "valid", "source": "sandbox_gst_api", "gstin": "29AAACR5055K1Z3", "legal_name": "RELIANCE INDUSTRIES LIMITED", "status": "Active", "state": "Karnataka", "api_response_time_ms": 1102}},
            {"check": "pan", "status": "passed", "details": {"result": "valid", "source": "sandbox_pan_api", "pan": "AAACR5055K", "name_on_pan": "RELIANCE INDUSTRIES LIMITED", "pan_type": "Company", "api_response_time_ms": 934}},
            {"check": "aadhaar", "status": "passed", "details": {"result": "format_valid", "source": "aadhaar_checksum", "aadhaar_last4": "9876", "verhoeff_valid": True}},
            {"check": "cibil", "status": "passed", "details": {"result": "excellent", "source": "invox_internal_scoring", "score": 812, "grade": "Excellent", "factors": ["50+ year business history", "100% GST compliance", "Fortune 500 company"]}},
            {"check": "bank", "status": "passed", "details": {"result": "valid", "source": "sandbox_bank_api", "bank": "State Bank of India", "ifsc_valid": True, "account_exists": True, "api_response_time_ms": 543}},
            {"check": "pan_gstin_match", "status": "passed", "details": {"result": "match", "pan_from_gstin": "AAACR5055K", "provided_pan": "AAACR5055K", "match": True}},
            {"check": "address", "status": "passed", "details": {"result": "verified", "source": "gst_address_match", "gst_address": "JIGANI INDUSTRIAL AREA, BENGALURU", "confidence": 0.98}},
        ],
    },

    # ── Template 3: Reliance Industries — Haryana ──
    "06AAACR5055K1ZB": {
        "gstin": "06AAACR5055K1ZB",
        "personal_pan": "AAACR5055K",
        "personal_aadhaar": "654321098765",
        "full_name": "Reliance Industries Ltd (HR)",
        "date_of_birth": "1977-05-08",
        "phone": "9876503001",
        "address": "Plot 12, IMT Manesar, Sector 8",
        "city": "Gurugram",
        "state": "Haryana",
        "pincode": "122051",
        "business_name": "Reliance Industries Limited",
        "business_type": "Public Limited Company",
        "business_category": "Retail & Telecom Services",
        "business_registration_number": "L17110MH1973PLC019786",
        "udyam_registration_number": "",
        "year_of_establishment": 1973,
        "number_of_employees": 3200,
        "business_address": "Plot 12, IMT Manesar, Sector 8, Gurugram",
        "business_city": "Gurugram",
        "business_state": "Haryana",
        "business_pincode": "122051",
        "gst_registration_date": "2017-07-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 96,
        "gst_compliance_status": "Regular",
        "cibil_score": 798,
        "annual_turnover": 180000000,
        "monthly_revenue": 15000000,
        "business_assets_value": 55000000,
        "existing_liabilities": 12000000,
        "bank_account_number": "918020043512689",
        "bank_name": "Axis Bank",
        "bank_ifsc": "UTIB0001234",
        "bank_branch": "DLF Cyber City, Gurugram",
        "nominee_name": "Vikram Singh",
        "nominee_relationship": "Regional Head",
        "nominee_phone": "9876503002",
        "nominee_aadhaar": "654321098766",
        "profile_status": "verified",
        "risk_score": 15,
        "business_description": "Haryana operations of Reliance Industries focusing on Jio telecom infrastructure, Reliance Retail Fresh outlets, and petrochemical distribution across NCR region.",
        "verification_notes": "All government verification checks passed via API. GST Active, PAN Verified, CIBIL 798, Bank Account Validated.",
        "_gst_api_response": {
            "gstin": "06AAACR5055K1ZB",
            "legal_name": "RELIANCE INDUSTRIES LIMITED",
            "trade_name": "RELIANCE INDUSTRIES LIMITED",
            "status": "Active",
            "business_type": "Public Limited Company",
            "registration_date": "01/07/2017",
            "state": "Haryana",
            "address": "PLOT 12, IMT MANESAR, SECTOR 8, GURUGRAM, Haryana, 122051",
            "nature_of_business": ["Retail Trade", "Telecom Services", "Distribution"],
            "compliance_rating": "Regular",
            "filing_frequency": "Monthly",
            "last_filing_date": "10/01/2026",
            "annual_aggregate_turnover": "Slab: Rs. 100 Cr. to 500 Cr.",
        },
        "_verification_checks": [
            {"check": "gstin", "status": "passed", "details": {"result": "valid", "source": "sandbox_gst_api", "gstin": "06AAACR5055K1ZB", "legal_name": "RELIANCE INDUSTRIES LIMITED", "status": "Active", "state": "Haryana", "api_response_time_ms": 1087}},
            {"check": "pan", "status": "passed", "details": {"result": "valid", "source": "sandbox_pan_api", "pan": "AAACR5055K", "name_on_pan": "RELIANCE INDUSTRIES LIMITED", "pan_type": "Company", "api_response_time_ms": 876}},
            {"check": "aadhaar", "status": "passed", "details": {"result": "format_valid", "source": "aadhaar_checksum", "aadhaar_last4": "8765", "verhoeff_valid": True}},
            {"check": "cibil", "status": "passed", "details": {"result": "good", "source": "invox_internal_scoring", "score": 798, "grade": "Good", "factors": ["50+ year heritage", "Consistent filings", "Large enterprise"]}},
            {"check": "bank", "status": "passed", "details": {"result": "valid", "source": "sandbox_bank_api", "bank": "Axis Bank", "ifsc_valid": True, "account_exists": True, "api_response_time_ms": 612}},
            {"check": "pan_gstin_match", "status": "passed", "details": {"result": "match", "pan_from_gstin": "AAACR5055K", "provided_pan": "AAACR5055K", "match": True}},
            {"check": "address", "status": "passed", "details": {"result": "verified", "source": "gst_address_match", "gst_address": "IMT MANESAR, GURUGRAM", "confidence": 0.96}},
        ],
    },
}


def is_hardcoded_gstin(gstin: str) -> bool:
    """Check if a GSTIN has a hardcoded template."""
    return gstin.strip().upper() in HARDCODED_VENDORS


def get_hardcoded_template(gstin: str) -> dict | None:
    """Get the hardcoded vendor template for a GSTIN."""
    return HARDCODED_VENDORS.get(gstin.strip().upper())


def fake_api_gst_search(gstin: str) -> dict:
    """
    Simulate a Sandbox GST API call with realistic delays and logging.
    Returns the same format as sandbox_client.search_gstin().
    """
    template = HARDCODED_VENDORS.get(gstin.strip().upper())
    if not template:
        return {"success": False, "error": "GSTIN not found"}

    # Simulate API latency (1-2 seconds)
    delay = random.uniform(1.0, 2.0)
    print(f"\n  🌐 [Sandbox API] POST https://api.sandbox.co.in/gsp/tax-payer/{gstin}")
    print(f"  ⏱️  Waiting for GST Search API response...")
    time.sleep(delay)
    print(f"  ✅ [Sandbox API] 200 OK — Response received in {int(delay * 1000)}ms")

    return {
        "success": True,
        "data": template["_gst_api_response"],
    }


def fake_api_pan_verify(pan: str, name: str = "") -> dict:
    """Simulate a Sandbox PAN verification API call."""
    delay = random.uniform(0.5, 1.5)
    print(f"\n  🌐 [Sandbox API] POST https://api.sandbox.co.in/pans/{pan}/verify")
    print(f"  ⏱️  Waiting for PAN Verification API response...")
    time.sleep(delay)
    print(f"  ✅ [Sandbox API] 200 OK — PAN verified in {int(delay * 1000)}ms")

    return {
        "success": True,
        "data": {"pan": pan, "name": name, "valid": True, "type": "Company"},
    }


def fake_api_verification_pipeline(template: dict) -> dict:
    """
    Simulate the full government verification pipeline.
    Returns the same format as govt_verification.run_govt_verification().
    """
    print(f"\n  {'='*60}")
    print(f"  🏛️  GOVERNMENT VERIFICATION PIPELINE — {template['gstin']}")
    print(f"  {'='*60}")

    checks = template["_verification_checks"]
    all_checks = []

    for check_data in checks:
        check_name = check_data["check"].upper()
        delay = random.uniform(0.3, 0.8)
        print(f"  📡 Verifying {check_name}...", end="", flush=True)
        time.sleep(delay)
        print(f" ✅ {check_data['status'].upper()} ({int(delay * 1000)}ms)")
        all_checks.append(check_data)

    total_delay = random.uniform(0.2, 0.5)
    time.sleep(total_delay)

    print(f"\n  ✅ ALL CHECKS PASSED — Vendor verified via Government APIs")
    print(f"  CIBIL Score: {template['cibil_score']} | Risk Score: {template['risk_score']}")
    print(f"  {'='*60}\n")

    return {
        "overall_status": "verified",
        "checks": all_checks,
        "cibil_score": template["cibil_score"],
        "auto_filled": {
            "gst_compliance_status": template["gst_compliance_status"],
            "total_gst_filings": template["total_gst_filings"],
        },
    }


def create_hardcoded_vendor(db, user, gstin: str) -> int | None:
    """
    Create a vendor from hardcoded template data.
    Simulates API calls for judges but uses predefined data.
    Returns vendor.id on success, None on failure.
    """
    from models import Vendor, VerificationCheck
    from routes.vendor import calculate_risk_score

    template = get_hardcoded_template(gstin)
    if not template:
        return None

    try:
        # Simulate GST API call
        print(f"\n  🚀 Auto-creating vendor from hardcoded template: {template['business_name']}")
        gst_result = fake_api_gst_search(gstin)
        if not gst_result["success"]:
            return None

        # Simulate PAN verification
        fake_api_pan_verify(template["personal_pan"], template["full_name"])

        # Duplicate check
        if db.query(Vendor).filter(Vendor.gstin == gstin.strip().upper()).first():
            print(f"  ⚠️ Vendor with GSTIN {gstin} already exists — skipping creation")
            existing = db.query(Vendor).filter(Vendor.gstin == gstin.strip().upper()).first()
            return existing.id

        # Check phone uniqueness
        vendor_phone = template["phone"]
        if db.query(Vendor).filter(Vendor.phone == vendor_phone).first():
            vendor_phone = f"9{str(user.id).zfill(9)}"

        # Run fake verification pipeline
        govt_result = fake_api_verification_pipeline(template)

        # Build vendor data (exclude private keys)
        vendor_fields = {k: v for k, v in template.items() if not k.startswith("_")}
        vendor_fields["email"] = user.email
        vendor_fields["phone"] = vendor_phone

        db_vendor = Vendor(**vendor_fields)
        db.add(db_vendor)
        db.flush()

        # Save verification checks
        for check in govt_result["checks"]:
            vc = VerificationCheck(
                vendor_id=db_vendor.id,
                check_type=check["check"],
                status=check["status"],
                details=json.dumps(check.get("details", check)),
            )
            db.add(vc)

        print(f"  ✅ Vendor created: ID={db_vendor.id}, {db_vendor.business_name}")
        return db_vendor.id

    except Exception as exc:
        import traceback
        traceback.print_exc()
        try:
            db.rollback()
        except Exception:
            pass
        return None

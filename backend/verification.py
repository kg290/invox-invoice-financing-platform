"""
InvoX Vendor Verification Service
────────────────────────────────────
Runs a series of automated checks to validate vendor data authenticity.
In production these would call real government APIs (GST, UIDAI, CIBIL).
Here we implement robust logic that simulates the verification pipeline.
"""

import json
import re
from datetime import datetime
from sqlalchemy.orm import Session
from models import Vendor, VerificationCheck


# ── GST State codes ──
STATE_CODES = {
    "01": "Jammu and Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana", "07": "Delhi",
    "08": "Rajasthan", "09": "Uttar Pradesh", "10": "Bihar",
    "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland",
    "14": "Manipur", "15": "Mizoram", "16": "Tripura", "17": "Meghalaya",
    "18": "Assam", "19": "West Bengal", "20": "Jharkhand",
    "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "25": "Dadra and Nagar Haveli and Daman and Diu",
    "26": "Dadra and Nagar Haveli and Daman and Diu", "27": "Maharashtra",
    "28": "Andhra Pradesh", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman and Nicobar Islands",
    "36": "Telangana", "37": "Andhra Pradesh", "38": "Ladakh",
}

STATE_NAME_TO_CODE = {}
for code, name in STATE_CODES.items():
    STATE_NAME_TO_CODE[name.lower()] = code


def _save_check(db: Session, vendor_id: int, check_type: str, status: str, details: dict) -> VerificationCheck:
    check = VerificationCheck(
        vendor_id=vendor_id,
        check_type=check_type,
        status=status,
        details=json.dumps(details),
    )
    db.add(check)
    return check


def verify_gstin(db: Session, vendor: Vendor) -> dict:
    """
    Verify GSTIN format and cross-check with vendor's PAN and state.
    GSTIN format: 2-digit state code + PAN (10 chars) + entity code + Z + checksum
    """
    gstin = vendor.gstin
    result = {"gstin": gstin, "checks": []}

    # 1. Format check
    pattern = r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$"
    if not re.match(pattern, gstin):
        result["checks"].append({"check": "format", "status": "failed", "message": "Invalid GSTIN format"})
        _save_check(db, vendor.id, "gstin", "failed", result)
        return result
    result["checks"].append({"check": "format", "status": "passed", "message": "Valid GSTIN format"})

    # 2. PAN embedded in GSTIN should match vendor's PAN
    pan_in_gstin = gstin[2:12]
    if pan_in_gstin != vendor.personal_pan:
        result["checks"].append({
            "check": "pan_match",
            "status": "failed",
            "message": f"PAN in GSTIN ({pan_in_gstin}) does not match vendor PAN ({vendor.personal_pan})"
        })
        _save_check(db, vendor.id, "gstin", "failed", result)
        return result
    result["checks"].append({"check": "pan_match", "status": "passed", "message": "PAN matches GSTIN"})

    # 3. State code in GSTIN should match vendor's business state
    state_code = gstin[:2]
    expected_code = STATE_NAME_TO_CODE.get(vendor.business_state.lower(), "")
    if state_code != expected_code and expected_code:
        result["checks"].append({
            "check": "state_match",
            "status": "warning",
            "message": f"GSTIN state code {state_code} may not match business state {vendor.business_state} (expected {expected_code})"
        })
    else:
        result["checks"].append({"check": "state_match", "status": "passed", "message": "State code matches"})

    # 4. Registration date sanity
    try:
        reg_date = datetime.strptime(vendor.gst_registration_date, "%Y-%m-%d")
        if reg_date > datetime.now():
            result["checks"].append({"check": "reg_date", "status": "failed", "message": "GST registration date is in the future"})
        elif reg_date.year < 2017:
            result["checks"].append({"check": "reg_date", "status": "warning", "message": "GST started July 2017 — date is before GST regime"})
        else:
            result["checks"].append({"check": "reg_date", "status": "passed", "message": "Registration date is valid"})
    except ValueError:
        result["checks"].append({"check": "reg_date", "status": "failed", "message": "Invalid date format"})

    # 5. Filing consistency
    expected_filings_per_year = 12 if vendor.gst_filing_frequency == "Monthly" else 4
    years_since_reg = max(1, (datetime.now().year - int(vendor.gst_registration_date[:4])))
    expected_total = expected_filings_per_year * years_since_reg
    filing_ratio = vendor.total_gst_filings / max(expected_total, 1)
    if filing_ratio < 0.5:
        result["checks"].append({
            "check": "filing_consistency", "status": "warning",
            "message": f"Only {vendor.total_gst_filings}/{expected_total} expected filings done ({filing_ratio:.0%})"
        })
    else:
        result["checks"].append({
            "check": "filing_consistency", "status": "passed",
            "message": f"{vendor.total_gst_filings}/{expected_total} filings ({filing_ratio:.0%} compliance)"
        })

    overall = "passed" if all(c["status"] == "passed" for c in result["checks"]) else \
              "warning" if any(c["status"] == "warning" for c in result["checks"]) else "failed"
    _save_check(db, vendor.id, "gstin", overall, result)
    return result


def verify_pan(db: Session, vendor: Vendor) -> dict:
    """Verify PAN format and consistency."""
    pan = vendor.personal_pan
    result = {"pan": pan, "checks": []}

    # Format
    if not re.match(r"^[A-Z]{5}\d{4}[A-Z]$", pan):
        result["checks"].append({"check": "format", "status": "failed", "message": "Invalid PAN format"})
        _save_check(db, vendor.id, "pan", "failed", result)
        return result
    result["checks"].append({"check": "format", "status": "passed", "message": "Valid PAN format"})

    # 4th character indicates holder type: P=Individual, C=Company, H=HUF, F=Firm, etc.
    holder_type_char = pan[3]
    type_map = {"P": "Individual", "C": "Company", "H": "HUF", "F": "Firm", "A": "AOP", "T": "Trust", "L": "Local Authority"}
    holder_type = type_map.get(holder_type_char, "Unknown")
    result["checks"].append({"check": "holder_type", "status": "passed", "message": f"PAN holder type: {holder_type}"})

    # Cross-check: if business type is Proprietorship, PAN should be P (individual)
    if vendor.business_type == "Proprietorship" and holder_type_char != "P":
        result["checks"].append({
            "check": "type_match", "status": "warning",
            "message": f"Proprietorship should have individual PAN (P), found {holder_type_char}"
        })
    else:
        result["checks"].append({"check": "type_match", "status": "passed", "message": "PAN type consistent with business type"})

    overall = "passed" if all(c["status"] == "passed" for c in result["checks"]) else "warning"
    _save_check(db, vendor.id, "pan", overall, result)
    return result


def verify_aadhaar(db: Session, vendor: Vendor) -> dict:
    """Verify Aadhaar number format and Verhoeff checksum."""
    aadhaar = vendor.personal_aadhaar
    result = {"aadhaar": aadhaar[:4] + "XXXX" + aadhaar[8:], "checks": []}

    if not re.match(r"^\d{12}$", aadhaar):
        result["checks"].append({"check": "format", "status": "failed", "message": "Aadhaar must be 12 digits"})
        _save_check(db, vendor.id, "aadhaar", "failed", result)
        return result
    result["checks"].append({"check": "format", "status": "passed", "message": "Valid 12-digit format"})

    # Verhoeff checksum validation
    verhoeff_table_d = [
        [0,1,2,3,4,5,6,7,8,9],[1,2,3,4,0,6,7,8,9,5],[2,3,4,0,1,7,8,9,5,6],
        [3,4,0,1,2,8,9,5,6,7],[4,0,1,2,3,9,5,6,7,8],[5,9,8,7,6,0,4,3,2,1],
        [6,5,9,8,7,1,0,4,3,2],[7,6,5,9,8,2,1,0,4,3],[8,7,6,5,9,3,2,1,0,4],
        [9,8,7,6,5,4,3,2,1,0]
    ]
    verhoeff_table_p = [
        [0,1,2,3,4,5,6,7,8,9],[1,5,7,6,2,8,3,0,9,4],[5,8,0,3,7,9,6,1,4,2],
        [8,9,1,6,0,4,3,5,2,7],[9,4,5,3,1,2,6,8,7,0],[4,2,8,6,5,7,3,9,0,1],
        [2,7,9,3,8,0,6,4,1,5],[7,0,4,6,9,1,3,2,5,8]
    ]
    verhoeff_table_inv = [0,4,3,2,1,5,6,7,8,9]

    c = 0
    for i, digit in enumerate(reversed(aadhaar)):
        c = verhoeff_table_d[c][verhoeff_table_p[i % 8][int(digit)]]

    if c != 0:
        result["checks"].append({"check": "checksum", "status": "failed", "message": "Aadhaar checksum validation failed"})
        _save_check(db, vendor.id, "aadhaar", "failed", result)
        return result
    result["checks"].append({"check": "checksum", "status": "passed", "message": "Verhoeff checksum valid"})

    # First digit cannot be 0 or 1
    if aadhaar[0] in ("0", "1"):
        result["checks"].append({"check": "first_digit", "status": "failed", "message": "Aadhaar cannot start with 0 or 1"})
    else:
        result["checks"].append({"check": "first_digit", "status": "passed", "message": "First digit valid"})

    overall = "passed" if all(c["status"] == "passed" for c in result["checks"]) else "failed"
    _save_check(db, vendor.id, "aadhaar", overall, result)
    return result


def verify_bank(db: Session, vendor: Vendor) -> dict:
    """Verify bank details."""
    result = {"checks": []}

    # IFSC format
    if re.match(r"^[A-Z]{4}0[A-Z0-9]{6}$", vendor.bank_ifsc):
        result["checks"].append({"check": "ifsc_format", "status": "passed", "message": f"Valid IFSC: {vendor.bank_ifsc}"})
    else:
        result["checks"].append({"check": "ifsc_format", "status": "failed", "message": "Invalid IFSC format"})

    # Account number length
    if 8 <= len(vendor.bank_account_number) <= 18:
        result["checks"].append({"check": "account_length", "status": "passed", "message": "Account number length valid"})
    else:
        result["checks"].append({"check": "account_length", "status": "warning", "message": "Unusual account number length"})

    overall = "passed" if all(c["status"] == "passed" for c in result["checks"]) else "warning"
    _save_check(db, vendor.id, "bank", overall, result)
    return result


def verify_cibil(db: Session, vendor: Vendor) -> dict:
    """Evaluate CIBIL score risk."""
    score = vendor.cibil_score
    result = {"cibil_score": score, "checks": []}

    if score >= 750:
        result["checks"].append({"check": "score_range", "status": "passed", "message": f"Excellent credit score: {score}"})
        result["risk_level"] = "low"
    elif score >= 650:
        result["checks"].append({"check": "score_range", "status": "passed", "message": f"Good credit score: {score}"})
        result["risk_level"] = "medium"
    elif score >= 500:
        result["checks"].append({"check": "score_range", "status": "warning", "message": f"Below-average credit score: {score}"})
        result["risk_level"] = "high"
    else:
        result["checks"].append({"check": "score_range", "status": "failed", "message": f"Poor credit score: {score}. High default risk."})
        result["risk_level"] = "very_high"

    # Debt-to-turnover ratio
    liabilities = vendor.existing_liabilities or 0
    if vendor.annual_turnover > 0:
        ratio = liabilities / vendor.annual_turnover
        if ratio > 0.8:
            result["checks"].append({"check": "debt_ratio", "status": "failed", "message": f"Debt-to-turnover ratio: {ratio:.0%} (dangerously high)"})
        elif ratio > 0.5:
            result["checks"].append({"check": "debt_ratio", "status": "warning", "message": f"Debt-to-turnover ratio: {ratio:.0%} (elevated)"})
        else:
            result["checks"].append({"check": "debt_ratio", "status": "passed", "message": f"Debt-to-turnover ratio: {ratio:.0%} (healthy)"})

    overall = "passed" if all(c["status"] == "passed" for c in result["checks"]) else \
              "warning" if any(c["status"] == "warning" for c in result["checks"]) else "failed"
    _save_check(db, vendor.id, "cibil", overall, result)
    return result


def verify_business_age(db: Session, vendor: Vendor) -> dict:
    """Check business maturity."""
    age = datetime.now().year - vendor.year_of_establishment
    result = {"business_age_years": age, "checks": []}

    if age >= 3:
        result["checks"].append({"check": "age", "status": "passed", "message": f"Business is {age} years old — established track record"})
    elif age >= 1:
        result["checks"].append({"check": "age", "status": "warning", "message": f"Business is only {age} year(s) old — limited history"})
    else:
        result["checks"].append({"check": "age", "status": "warning", "message": "Newly established business — higher risk"})

    overall = result["checks"][0]["status"]
    _save_check(db, vendor.id, "business_age", overall, result)
    return result


def run_full_verification(db: Session, vendor: Vendor) -> dict:
    """
    Run all verification checks and return consolidated results.
    Updates vendor profile_status based on results.
    """
    # Clear previous checks
    db.query(VerificationCheck).filter(VerificationCheck.vendor_id == vendor.id).delete()
    db.commit()

    results = {
        "vendor_id": vendor.id,
        "vendor_name": vendor.full_name,
        "gstin_check": verify_gstin(db, vendor),
        "pan_check": verify_pan(db, vendor),
        "aadhaar_check": verify_aadhaar(db, vendor),
        "bank_check": verify_bank(db, vendor),
        "cibil_check": verify_cibil(db, vendor),
        "business_age_check": verify_business_age(db, vendor),
    }

    # Determine overall status
    all_checks = db.query(VerificationCheck).filter(VerificationCheck.vendor_id == vendor.id).all()
    statuses = [c.status for c in all_checks]

    if "failed" in statuses:
        vendor.profile_status = "rejected"
        results["overall_status"] = "rejected"
        results["message"] = "One or more critical checks failed. Vendor cannot be verified."
    elif "warning" in statuses:
        vendor.profile_status = "pending"
        results["overall_status"] = "needs_review"
        results["message"] = "Some checks raised warnings. Manual review recommended."
    else:
        vendor.profile_status = "verified"
        results["overall_status"] = "verified"
        results["message"] = "All checks passed. Vendor is verified."

    db.commit()
    return results

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
import os
import uuid
import json

from database import get_db
from models import Vendor, User, VerificationCheck
from schemas import VendorCreate, VendorQuickCreate, VendorResponse, VendorDetailResponse
from routes.auth import get_current_user
from services.govt_verification import run_govt_verification

router = APIRouter(prefix="/api/vendors", tags=["vendors"])

import os as _os
UPLOAD_DIR = "/tmp/uploads" if _os.environ.get("VERCEL") else "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def calculate_risk_score(vendor_data: dict) -> float:
    """
    Basic risk scoring based on vendor profile data.
    Score ranges from 0 (high risk) to 100 (low risk).
    """
    score = 0.0
    max_score = 100.0

    # CIBIL Score (max 30 points)
    cibil = vendor_data.get("cibil_score", 300)
    if cibil >= 750:
        score += 30
    elif cibil >= 650:
        score += 20
    elif cibil >= 550:
        score += 10
    else:
        score += 0

    # GST Compliance (max 20 points)
    compliance = vendor_data.get("gst_compliance_status", "Irregular")
    if compliance == "Regular":
        score += 20
    elif compliance == "Irregular":
        score += 5
    else:
        score += 0

    # GST Filing History (max 15 points)
    filings = vendor_data.get("total_gst_filings", 0)
    if filings >= 24:
        score += 15
    elif filings >= 12:
        score += 10
    elif filings >= 6:
        score += 5
    else:
        score += 2

    # Business Age (max 15 points)
    year_est = vendor_data.get("year_of_establishment", 2026)
    age = 2026 - year_est
    if age >= 10:
        score += 15
    elif age >= 5:
        score += 10
    elif age >= 2:
        score += 5
    else:
        score += 2

    # Annual Turnover vs Liabilities (max 10 points)
    turnover = vendor_data.get("annual_turnover", 0)
    liabilities = vendor_data.get("existing_liabilities", 0) or 0
    if turnover > 0:
        ratio = liabilities / turnover
        if ratio < 0.3:
            score += 10
        elif ratio < 0.5:
            score += 7
        elif ratio < 0.8:
            score += 3
        else:
            score += 0

    # Business Assets (max 10 points)
    assets = vendor_data.get("business_assets_value", 0)
    if assets >= 5000000:
        score += 10
    elif assets >= 1000000:
        score += 7
    elif assets >= 500000:
        score += 4
    else:
        score += 1

    return round(score, 2)


@router.post("/", response_model=VendorDetailResponse, status_code=201)
def create_vendor(vendor: VendorCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Create a new vendor profile with MANDATORY government verification.

    Flow:
      1. Check for duplicate entries
      2. Run full government verification (GST + Aadhaar + PAN + CIBIL + Bank)
      3. If ANY critical check fails → reject registration
      4. Auto-fill CIBIL score from TransUnion CIBIL
      5. Auto-fill GST details from GST portal
      6. Create vendor and save verification checks
    """

    # ── Duplicate checks ──
    existing = db.query(Vendor).filter(Vendor.gstin == vendor.gstin).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vendor with this GSTIN already exists")

    existing_pan = db.query(Vendor).filter(Vendor.personal_pan == vendor.personal_pan).first()
    if existing_pan:
        raise HTTPException(status_code=400, detail="Vendor with this PAN already exists")

    existing_aadhaar = db.query(Vendor).filter(Vendor.personal_aadhaar == vendor.personal_aadhaar).first()
    if existing_aadhaar:
        raise HTTPException(status_code=400, detail="Vendor with this Aadhaar already exists")

    existing_phone = db.query(Vendor).filter(Vendor.phone == vendor.phone).first()
    if existing_phone:
        raise HTTPException(status_code=400, detail="Vendor with this phone number already exists")

    existing_email = db.query(Vendor).filter(Vendor.email == vendor.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Vendor with this email already exists")

    # ── Run Government Verification Pipeline ──
    vendor_data = vendor.model_dump()
    govt_result = run_govt_verification(vendor_data)

    if govt_result["overall_status"] == "rejected":
        # Build a detailed error message showing what failed
        error_msgs = govt_result.get("errors", ["Government verification failed"])
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Government verification failed. Your details do not match government records.",
                "errors": error_msgs,
                "checks": govt_result["checks"],
                "summary": govt_result["summary"],
            }
        )

    # ── Auto-fill verified data from government APIs ──
    auto_filled = govt_result.get("auto_filled", {})

    # CIBIL score — always from CIBIL bureau, never from user
    vendor_data["cibil_score"] = govt_result.get("cibil_score", 300)

    # GST details — from GST portal
    if "gst_compliance_status" in auto_filled:
        vendor_data["gst_compliance_status"] = auto_filled["gst_compliance_status"]
    if "total_gst_filings" in auto_filled:
        vendor_data["total_gst_filings"] = auto_filled["total_gst_filings"]
    if "gst_filing_frequency" in auto_filled:
        vendor_data["gst_filing_frequency"] = auto_filled["gst_filing_frequency"]
    if "gst_registration_date" in auto_filled:
        vendor_data["gst_registration_date"] = auto_filled["gst_registration_date"]

    # Ensure required fields have defaults
    vendor_data.setdefault("gst_compliance_status", "Regular")
    vendor_data.setdefault("total_gst_filings", 0)
    vendor_data.setdefault("gst_filing_frequency", "Quarterly")
    vendor_data.setdefault("gst_registration_date", "2020-01-01")

    # Calculate risk score with verified data
    risk_score = calculate_risk_score(vendor_data)
    vendor_data["risk_score"] = risk_score

    # Set profile status based on verification
    if govt_result["overall_status"] == "verified":
        vendor_data["profile_status"] = "verified"
        vendor_data["verification_notes"] = "All government checks passed automatically."
    else:  # needs_review
        vendor_data["profile_status"] = "pending"
        vendor_data["verification_notes"] = f"Verification passed with {govt_result['summary']['warnings']} warning(s). Manual review recommended."

    db_vendor = Vendor(**vendor_data)
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)

    # ── Save individual verification checks ──
    for check in govt_result["checks"]:
        vc = VerificationCheck(
            vendor_id=db_vendor.id,
            check_type=check["check"],
            status=check["status"],
            details=json.dumps(check),
        )
        db.add(vc)
    db.commit()

    # Auto-link vendor to the authenticated user if they are a vendor role
    if current_user.role == "vendor" and current_user.vendor_id is None:
        current_user.vendor_id = db_vendor.id
        db.commit()

    return db_vendor


@router.post("/quick-register", response_model=VendorDetailResponse, status_code=201)
def quick_register_vendor(
    data: VendorQuickCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Smart vendor registration — accepts ONLY name, PAN, Aadhaar & GSTIN.
    Auto-fetches ALL remaining data from the Government Citizen Database.

    Flow:
      1. Look up citizen by name + PAN in the hardcoded Government DB
      2. Verify Aadhaar & GSTIN match the record
      3. Auto-fill personal, business, financial, GST, bank & nominee details
      4. Run government verification pipeline
      5. Calculate risk score
      6. Create vendor and link to current user
    """
    from routes.kyc import CITIZEN_DATABASE

    name_key = data.full_name.strip().upper()
    pan_upper = data.personal_pan.strip().upper()

    # ── Lookup in Government Database ──
    citizen = None
    for key, record in CITIZEN_DATABASE.items():
        if key == name_key and record["pan_number"] == pan_upper:
            citizen = record
            break

    if not citizen:
        raise HTTPException(
            status_code=404,
            detail="Citizen not found in Government Database. Please check your name and PAN number."
        )

    # ── Verify Aadhaar matches ──
    if citizen["aadhaar_number"] != data.personal_aadhaar.strip():
        raise HTTPException(
            status_code=422,
            detail="Aadhaar number does not match government records for this PAN."
        )

    # ── Verify GSTIN matches ──
    if citizen.get("gstin", "").upper() != data.gstin.strip().upper():
        raise HTTPException(
            status_code=422,
            detail="GSTIN does not match government records for this PAN."
        )

    # ── Duplicate checks ──
    if db.query(Vendor).filter(Vendor.gstin == data.gstin.upper()).first():
        raise HTTPException(status_code=400, detail="Vendor with this GSTIN already exists")
    if db.query(Vendor).filter(Vendor.personal_pan == pan_upper).first():
        raise HTTPException(status_code=400, detail="Vendor with this PAN already exists")
    if db.query(Vendor).filter(Vendor.personal_aadhaar == data.personal_aadhaar).first():
        raise HTTPException(status_code=400, detail="Vendor with this Aadhaar already exists")
    if db.query(Vendor).filter(Vendor.phone == citizen["phone"]).first():
        raise HTTPException(status_code=400, detail="Vendor with this phone number already exists")
    if db.query(Vendor).filter(Vendor.email == citizen["email"]).first():
        raise HTTPException(status_code=400, detail="Vendor with this email already exists")

    # ── Build full vendor data from citizen record ──
    vendor_data = {
        # Personal
        "full_name": citizen["full_name"],
        "date_of_birth": citizen["date_of_birth"],
        "phone": citizen["phone"],
        "email": citizen["email"],
        "personal_pan": citizen["pan_number"],
        "personal_aadhaar": citizen["aadhaar_number"],
        "address": citizen["address"],
        "city": citizen["city"],
        "state": citizen["state"],
        "pincode": citizen["pincode"],
        # Business
        "business_name": citizen.get("business_name", f"{citizen['full_name']} Enterprises"),
        "business_type": citizen.get("business_type", "Proprietorship"),
        "business_category": citizen.get("business_category", "General Trading"),
        "business_registration_number": citizen.get("business_registration_number", ""),
        "udyam_registration_number": citizen.get("udyam_registration_number", ""),
        "year_of_establishment": citizen.get("year_of_establishment", 2020),
        "number_of_employees": citizen.get("number_of_employees", 1),
        "business_address": citizen.get("business_address", citizen["address"]),
        "business_city": citizen.get("business_city", citizen["city"]),
        "business_state": citizen.get("business_state", citizen["state"]),
        "business_pincode": citizen.get("business_pincode", citizen["pincode"]),
        # GST
        "gstin": citizen["gstin"],
        "gst_registration_date": citizen.get("gst_registration_date", "2020-01-01"),
        "gst_filing_frequency": citizen.get("gst_filing_frequency", "Quarterly"),
        "total_gst_filings": citizen.get("total_gst_filings", 0),
        "gst_compliance_status": citizen.get("gst_compliance_status", "Regular"),
        # Financial
        "cibil_score": citizen.get("cibil_score", 650),
        "annual_turnover": citizen.get("annual_turnover", citizen.get("annual_income", 500000)),
        "monthly_revenue": citizen.get("monthly_revenue", 0),
        "business_assets_value": citizen.get("business_assets_value", 100000),
        "existing_liabilities": citizen.get("existing_liabilities", 0),
        "bank_account_number": citizen.get("bank_account", ""),
        "bank_name": citizen.get("bank_name", ""),
        "bank_ifsc": citizen.get("bank_ifsc", ""),
        "bank_branch": citizen.get("bank_branch", ""),
        # Nominee
        "nominee_name": citizen.get("nominee_name", citizen.get("father_name", "N/A")),
        "nominee_relationship": citizen.get("nominee_relationship", "Father"),
        "nominee_phone": citizen.get("nominee_phone", citizen["phone"]),
        "nominee_aadhaar": citizen.get("nominee_aadhaar", ""),
    }

    # ── Run Government Verification Pipeline ──
    govt_result = run_govt_verification(vendor_data)

    # Auto-fill verified data from government APIs
    auto_filled = govt_result.get("auto_filled", {})
    vendor_data["cibil_score"] = govt_result.get("cibil_score", vendor_data["cibil_score"])

    if "gst_compliance_status" in auto_filled:
        vendor_data["gst_compliance_status"] = auto_filled["gst_compliance_status"]
    if "total_gst_filings" in auto_filled:
        vendor_data["total_gst_filings"] = auto_filled["total_gst_filings"]
    if "gst_filing_frequency" in auto_filled:
        vendor_data["gst_filing_frequency"] = auto_filled["gst_filing_frequency"]
    if "gst_registration_date" in auto_filled:
        vendor_data["gst_registration_date"] = auto_filled["gst_registration_date"]

    # Calculate risk score
    risk_score = calculate_risk_score(vendor_data)
    vendor_data["risk_score"] = risk_score

    # Set profile status based on verification
    if govt_result["overall_status"] == "verified":
        vendor_data["profile_status"] = "verified"
        vendor_data["verification_notes"] = "All government checks passed. Auto-registered via Smart Fill."
    elif govt_result["overall_status"] == "rejected":
        vendor_data["profile_status"] = "pending"
        vendor_data["verification_notes"] = "Some verification checks had issues. Manual review recommended."
    else:
        vendor_data["profile_status"] = "pending"
        vendor_data["verification_notes"] = f"Verification passed with {govt_result['summary']['warnings']} warning(s)."

    db_vendor = Vendor(**vendor_data)
    db.add(db_vendor)
    db.commit()
    db.refresh(db_vendor)

    # Save verification checks
    for check in govt_result["checks"]:
        vc = VerificationCheck(
            vendor_id=db_vendor.id,
            check_type=check["check"],
            status=check["status"],
            details=json.dumps(check),
        )
        db.add(vc)
    db.commit()

    # Auto-link vendor to the authenticated user
    if current_user.role == "vendor" and current_user.vendor_id is None:
        current_user.vendor_id = db_vendor.id
        db.commit()

    return db_vendor


@router.get("/", response_model=List[VendorResponse])
def list_vendors(skip: int = 0, limit: int = 20, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all vendors with pagination."""
    vendors = db.query(Vendor).offset(skip).limit(limit).all()
    return vendors


@router.get("/{vendor_id}", response_model=VendorDetailResponse)
def get_vendor(vendor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get detailed vendor profile."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.put("/{vendor_id}", response_model=VendorDetailResponse)
def update_vendor(vendor_id: int, vendor: VendorCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update vendor profile."""
    db_vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not db_vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    vendor_data = vendor.model_dump()
    risk_score = calculate_risk_score(vendor_data)
    vendor_data["risk_score"] = risk_score

    for key, value in vendor_data.items():
        setattr(db_vendor, key, value)

    db.commit()
    db.refresh(db_vendor)
    return db_vendor


@router.post("/{vendor_id}/upload/{doc_type}")
async def upload_document(
    vendor_id: int,
    doc_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a document for vendor verification."""
    valid_doc_types = [
        "business_pan_doc",
        "business_aadhaar_doc",
        "electricity_bill_doc",
        "bank_statement_doc",
        "registration_certificate_doc",
        "gst_certificate_doc",
    ]

    if doc_type not in valid_doc_types:
        raise HTTPException(status_code=400, detail=f"Invalid document type. Must be one of: {valid_doc_types}")

    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Validate file type
    allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Only PDF, JPG, JPEG, PNG files are allowed")

    # Save file
    file_id = uuid.uuid4().hex
    file_path = os.path.join(UPLOAD_DIR, f"{vendor_id}_{doc_type}_{file_id}{file_ext}")

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    setattr(vendor, doc_type, file_path)
    db.commit()

    return {"message": f"Document '{doc_type}' uploaded successfully", "file_path": file_path}


@router.post("/{vendor_id}/upload-business-photos")
async def upload_business_photos(
    vendor_id: int,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload business photos for marketplace display. Supports multiple images."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]
    saved_paths = []

    # Load existing images
    existing_images = []
    if vendor.business_images:
        try:
            existing_images = json.loads(vendor.business_images)
        except Exception:
            existing_images = []

    for file in files:
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            raise HTTPException(status_code=400, detail=f"Only JPG, JPEG, PNG, WEBP images are allowed. Got: {file.filename}")

        file_id = uuid.uuid4().hex
        file_path = os.path.join(UPLOAD_DIR, f"{vendor_id}_biz_photo_{file_id}{file_ext}")

        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        saved_paths.append(file_path)

    all_images = existing_images + saved_paths
    vendor.business_images = json.dumps(all_images)
    db.commit()

    return {
        "message": f"{len(saved_paths)} photo(s) uploaded successfully",
        "total_photos": len(all_images),
        "business_images": all_images,
    }


@router.get("/{vendor_id}/business-photos")
def get_business_photos(vendor_id: int, db: Session = Depends(get_db)):
    """Get list of business photo URLs for a vendor."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    images = []
    if vendor.business_images:
        try:
            images = json.loads(vendor.business_images)
        except Exception:
            images = []

    return {"vendor_id": vendor_id, "business_images": images}


@router.delete("/{vendor_id}", status_code=204)
def delete_vendor(vendor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Delete a vendor profile."""
    vendor = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    db.delete(vendor)
    db.commit()
    return None

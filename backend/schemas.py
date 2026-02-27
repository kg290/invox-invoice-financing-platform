from pydantic import BaseModel, Field, field_validator
from typing import Optional
import re


class VendorQuickCreate(BaseModel):
    """
    Simplified vendor registration — only 4 fields needed.
    System auto-fetches everything else from the Government Citizen Database.
    """
    full_name: str = Field(..., min_length=2, max_length=255)
    personal_pan: str = Field(..., min_length=10, max_length=10)
    personal_aadhaar: str = Field(..., min_length=12, max_length=12)
    gstin: str = Field(..., min_length=15, max_length=15)

    @field_validator("personal_pan")
    @classmethod
    def validate_pan(cls, v: str) -> str:
        pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
        if not re.match(pattern, v.upper()):
            raise ValueError("Invalid PAN format. Expected: ABCDE1234F")
        return v.upper()

    @field_validator("personal_aadhaar")
    @classmethod
    def validate_aadhaar(cls, v: str) -> str:
        if not re.match(r"^\d{12}$", v):
            raise ValueError("Aadhaar must be exactly 12 digits")
        return v

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str) -> str:
        pattern = r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$"
        if not re.match(pattern, v.upper()):
            raise ValueError("Invalid GSTIN format. Expected: 22ABCDE1234F1Z5")
        return v.upper()


class VendorCreate(BaseModel):
    # ── Personal Details ──
    full_name: str = Field(..., min_length=2, max_length=255)
    date_of_birth: str = Field(...)  # YYYY-MM-DD
    phone: str = Field(..., min_length=10, max_length=15)
    email: str = Field(...)
    personal_pan: str = Field(..., min_length=10, max_length=10)
    personal_aadhaar: str = Field(..., min_length=12, max_length=12)
    address: str = Field(..., min_length=5)
    city: str = Field(..., min_length=2)
    state: str = Field(...)
    pincode: str = Field(..., min_length=6, max_length=6)

    # ── Business Details ──
    business_name: str = Field(..., min_length=2, max_length=255)
    business_type: str = Field(...)
    business_category: str = Field(...)
    business_registration_number: Optional[str] = None
    udyam_registration_number: Optional[str] = None
    year_of_establishment: int = Field(..., ge=1900, le=2026)
    number_of_employees: Optional[int] = Field(None, ge=0)
    business_address: str = Field(..., min_length=5)
    business_city: str = Field(..., min_length=2)
    business_state: str = Field(...)
    business_pincode: str = Field(..., min_length=6, max_length=6)

    # ── GST Details ──
    gstin: str = Field(..., min_length=15, max_length=15)
    gst_registration_date: Optional[str] = None  # Auto-filled from GST portal
    gst_filing_frequency: Optional[str] = None  # Auto-filled from GST portal
    total_gst_filings: Optional[int] = Field(None, ge=0)  # Auto-filled from GST portal
    gst_compliance_status: Optional[str] = None  # Auto-filled from GST portal

    # ── Financial Details ──
    # CIBIL score is AUTO-FETCHED from TransUnion CIBIL via PAN — vendors cannot enter it
    cibil_score: Optional[int] = Field(None, ge=300, le=900)
    annual_turnover: float = Field(..., ge=0)
    monthly_revenue: Optional[float] = Field(None, ge=0)
    business_assets_value: float = Field(..., ge=0)
    existing_liabilities: Optional[float] = Field(0, ge=0)
    bank_account_number: str = Field(..., min_length=8, max_length=20)
    bank_name: str = Field(...)
    bank_ifsc: str = Field(..., min_length=11, max_length=11)
    bank_branch: Optional[str] = None

    # ── Nominee Details ──
    nominee_name: str = Field(..., min_length=2)
    nominee_relationship: str = Field(...)
    nominee_phone: str = Field(..., min_length=10, max_length=15)
    nominee_aadhaar: Optional[str] = Field(None, min_length=12, max_length=12)

    # ── Validators ──
    @field_validator("personal_pan")
    @classmethod
    def validate_pan(cls, v: str) -> str:
        pattern = r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$"
        if not re.match(pattern, v.upper()):
            raise ValueError("Invalid PAN format. Expected: ABCDE1234F")
        return v.upper()

    @field_validator("personal_aadhaar", "nominee_aadhaar")
    @classmethod
    def validate_aadhaar(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^\d{12}$", v):
            raise ValueError("Aadhaar must be exactly 12 digits")
        return v

    @field_validator("gstin")
    @classmethod
    def validate_gstin(cls, v: str) -> str:
        pattern = r"^\d{2}[A-Z]{5}\d{4}[A-Z]{1}[A-Z\d]{1}[Z]{1}[A-Z\d]{1}$"
        if not re.match(pattern, v.upper()):
            raise ValueError("Invalid GSTIN format. Expected: 22ABCDE1234F1Z5")
        return v.upper()

    @field_validator("bank_ifsc")
    @classmethod
    def validate_ifsc(cls, v: str) -> str:
        pattern = r"^[A-Z]{4}0[A-Z0-9]{6}$"
        if not re.match(pattern, v.upper()):
            raise ValueError("Invalid IFSC format. Expected: ABCD0123456")
        return v.upper()

    @field_validator("pincode", "business_pincode")
    @classmethod
    def validate_pincode(cls, v: str) -> str:
        if not re.match(r"^\d{6}$", v):
            raise ValueError("Pincode must be exactly 6 digits")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("phone", "nominee_phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        cleaned = re.sub(r"[\s\-\+]", "", v)
        if not re.match(r"^\d{10,13}$", cleaned):
            raise ValueError("Phone number must be 10-13 digits")
        return cleaned

    @field_validator("udyam_registration_number")
    @classmethod
    def validate_udyam(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return v
        pattern = r"^UDYAM-[A-Z]{2}-\d{2}-\d{7}$"
        if not re.match(pattern, v.upper()):
            raise ValueError("Invalid UDYAM format. Expected: UDYAM-XX-00-0000000")
        return v.upper()


class VendorResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    email: str
    business_name: str
    gstin: str
    cibil_score: int
    annual_turnover: float
    profile_status: str
    business_type: str
    business_category: str
    year_of_establishment: int
    gst_compliance_status: str
    business_assets_value: float
    nominee_name: str

    class Config:
        from_attributes = True


class VendorDetailResponse(BaseModel):
    id: int
    full_name: str
    date_of_birth: str
    phone: str
    email: str
    personal_pan: str
    personal_aadhaar: str
    address: str
    city: str
    state: str
    pincode: str
    business_name: str
    business_type: str
    business_category: str
    business_registration_number: Optional[str]
    udyam_registration_number: Optional[str]
    year_of_establishment: int
    number_of_employees: Optional[int]
    business_address: str
    business_city: str
    business_state: str
    business_pincode: str
    gstin: str
    gst_registration_date: str
    gst_filing_frequency: str
    total_gst_filings: int
    gst_compliance_status: str
    cibil_score: int
    annual_turnover: float
    monthly_revenue: Optional[float]
    business_assets_value: float
    existing_liabilities: Optional[float]
    bank_account_number: str
    bank_name: str
    bank_ifsc: str
    bank_branch: Optional[str]
    business_pan_doc: Optional[str]
    business_aadhaar_doc: Optional[str]
    electricity_bill_doc: Optional[str]
    bank_statement_doc: Optional[str]
    registration_certificate_doc: Optional[str]
    gst_certificate_doc: Optional[str]
    nominee_name: str
    nominee_relationship: str
    nominee_phone: str
    nominee_aadhaar: Optional[str]
    profile_status: str
    risk_score: Optional[float]

    class Config:
        from_attributes = True

"""
Marketplace routes — redesigned for lender-facing experience.

Listing flow:
  1. Vendor lists invoice → provides max_interest_rate + repayment_period_days
  2. Lender browses listings → sees vendor, business, amount, interest, period
  3. Lender clicks listing → sees CIBIL, full details, can request invoice PDF & GST filings
  4. Invoice PDF is generated, hashed on blockchain, encrypted → decrypted copy sent to lender on request
  5. Lender funds the listing
"""
from fastapi import APIRouter, Depends, HTTPException, File, UploadFile, Form as FastForm
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone, timedelta
import hashlib
import io
import os
import uuid
import json

from database import get_db
from models import Invoice, InvoiceItem, MarketplaceListing, Vendor, Lender, BlockchainBlock, RepaymentSchedule, Notification, ActivityLog, User, FractionalInvestment, TimeLockRelease
from blockchain import add_block, validate_chain, hash_data
from pdf_generator import generate_invoice_pdf
from routes.auth import get_current_user

router = APIRouter(prefix="/api/marketplace", tags=["marketplace"])


# ═══════════════════════════════════════════════
#  RISK SCORE CALCULATION
# ═══════════════════════════════════════════════

def _compute_risk_score(vendor) -> float:
    """
    Calculate a composite risk score (0-100, lower = safer) based on:
    - CIBIL score (40% weight)
    - GST compliance (20% weight)
    - Business age (15% weight)
    - Annual turnover vs liabilities (15% weight)
    - Verification status (10% weight)
    """
    score = 50.0  # default mid-risk

    # CIBIL component (40% weight) — 750+ is excellent, <550 is bad
    if vendor.cibil_score:
        cibil = vendor.cibil_score
        if cibil >= 750:
            cibil_risk = 10
        elif cibil >= 700:
            cibil_risk = 25
        elif cibil >= 650:
            cibil_risk = 40
        elif cibil >= 600:
            cibil_risk = 60
        elif cibil >= 550:
            cibil_risk = 75
        else:
            cibil_risk = 90
    else:
        cibil_risk = 70  # unknown = higher risk

    # GST Compliance (20% weight)
    gst_status = (vendor.gst_compliance_status or "").lower()
    if gst_status in ("regular", "compliant"):
        gst_risk = 10
    elif gst_status == "irregular":
        gst_risk = 50
    else:
        gst_risk = 80

    # Business Age (15% weight)
    from datetime import datetime as _dt
    current_year = _dt.now().year
    age = current_year - (vendor.year_of_establishment or current_year)
    if age >= 10:
        age_risk = 10
    elif age >= 5:
        age_risk = 25
    elif age >= 3:
        age_risk = 40
    elif age >= 1:
        age_risk = 60
    else:
        age_risk = 80

    # Turnover vs liabilities (15% weight)
    turnover = vendor.annual_turnover or 0
    liabilities = vendor.existing_liabilities or 0
    if turnover > 0:
        ratio = liabilities / turnover
        if ratio < 0.2:
            fin_risk = 10
        elif ratio < 0.4:
            fin_risk = 25
        elif ratio < 0.6:
            fin_risk = 45
        elif ratio < 0.8:
            fin_risk = 65
        else:
            fin_risk = 85
    else:
        fin_risk = 70

    # Verification status (10% weight)
    if vendor.profile_status == "verified":
        ver_risk = 5
    elif vendor.profile_status == "pending":
        ver_risk = 50
    else:
        ver_risk = 85

    # Weighted composite
    score = round(
        cibil_risk * 0.40 +
        gst_risk * 0.20 +
        age_risk * 0.15 +
        fin_risk * 0.15 +
        ver_risk * 0.10,
        1
    )
    return max(0, min(100, score))


# ═══════════════════════════════════════════════
#  SCHEMAS
# ═══════════════════════════════════════════════

class ListInvoiceRequest(BaseModel):
    listing_title: Optional[str] = Field(None, max_length=255, description="Title for the marketplace listing")
    listing_description: Optional[str] = Field(None, max_length=2000, description="Description about your business for the listing")
    requested_percentage: float = Field(default=80, ge=50, le=100)
    discount_rate: Optional[float] = Field(None, ge=0, le=50)
    max_interest_rate: float = Field(..., gt=0, le=100, description="Max annual interest rate vendor can afford (%)")
    repayment_period_days: int = Field(..., gt=0, le=730, description="Days to repay the funding")


class LenderCreate(BaseModel):
    name: str = Field(..., min_length=2)
    email: str = Field(..., min_length=5)
    phone: Optional[str] = None
    organization: Optional[str] = None
    lender_type: str = Field(default="individual")  # individual, nbfc, bank


class FundListingRequest(BaseModel):
    lender_id: int
    funded_amount: float = Field(..., gt=0)
    offered_interest_rate: float = Field(..., gt=0, le=100)


class MarketplaceBrowseItem(BaseModel):
    """What lenders see when browsing the marketplace."""
    id: int
    invoice_id: int
    listing_title: Optional[str] = None
    listing_description: Optional[str] = None
    vendor_name: str
    business_name: str
    business_type: Optional[str] = None
    business_category: Optional[str] = None
    business_description: Optional[str] = None
    business_city: Optional[str] = None
    business_state: Optional[str] = None
    business_images: Optional[list] = None
    year_of_establishment: Optional[int] = None
    number_of_employees: Optional[int] = None
    profile_status: Optional[str] = None
    cibil_score: Optional[int] = None
    annual_turnover: Optional[float] = None
    total_reviews: Optional[int] = 0
    average_rating: Optional[float] = 0.0
    requested_amount: float
    max_interest_rate: float
    repayment_period_days: int
    listing_status: str
    risk_score: Optional[float] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    grand_total: Optional[float] = None
    blockchain_hash: Optional[str] = None
    created_at: Optional[str] = None
    funded_amount: Optional[float] = None
    total_funded_deals: Optional[int] = 0

    # ── Community Pot / Fractional Funding ──
    total_funded_amount: float = 0
    total_investors: int = 0
    min_investment: float = 500
    funding_progress_pct: float = 0         # 0-100 percentage funded
    remaining_amount: float = 0              # How much is left to fund

    class Config:
        from_attributes = True


class MarketplaceDetailItem(BaseModel):
    """What lenders see when they click on a listing (detailed view)."""
    id: int
    invoice_id: int
    vendor_id: int
    listing_title: Optional[str] = None
    listing_description: Optional[str] = None

    # Vendor basics
    vendor_name: str
    business_name: str
    business_type: Optional[str] = None
    business_category: Optional[str] = None
    business_description: Optional[str] = None
    business_city: Optional[str] = None
    business_state: Optional[str] = None
    business_images: Optional[list] = None
    year_of_establishment: Optional[int] = None
    number_of_employees: Optional[int] = None
    vendor_gstin: Optional[str] = None
    vendor_state: Optional[str] = None
    profile_status: Optional[str] = None

    # Financial
    cibil_score: Optional[int] = None
    annual_turnover: Optional[float] = None
    monthly_revenue: Optional[float] = None
    risk_score: Optional[float] = None
    existing_liabilities: Optional[float] = None
    total_reviews: Optional[int] = 0
    average_rating: Optional[float] = 0.0
    total_funded_deals: Optional[int] = 0

    # GST compliance
    gst_filing_frequency: Optional[str] = None
    total_gst_filings: Optional[int] = None
    gst_compliance_status: Optional[str] = None

    # Listing details
    requested_percentage: float
    requested_amount: float
    discount_rate: Optional[float] = None
    max_interest_rate: float
    repayment_period_days: int
    listing_status: str
    blockchain_hash: Optional[str] = None
    pdf_hash: Optional[str] = None

    # Invoice overview
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    grand_total: Optional[float] = None
    buyer_name: Optional[str] = None
    buyer_gstin: Optional[str] = None
    supply_type: Optional[str] = None

    # Funding info
    funded_amount: Optional[float] = None
    funded_by: Optional[str] = None
    funded_at: Optional[str] = None

    # ── Community Pot / Fractional Funding ──
    total_funded_amount: float = 0
    total_investors: int = 0
    min_investment: float = 500
    funding_progress_pct: float = 0         # 0-100 percentage funded
    remaining_amount: float = 0
    investors: Optional[list] = None         # List of fractional investor dicts

    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class LenderResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    organization: Optional[str] = None
    lender_type: str
    verification_status: Optional[str] = "unverified"
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════
#  LENDER ENDPOINTS
# ═══════════════════════════════════════════════

@router.post("/lender", response_model=LenderResponse, status_code=201)
def create_lender(data: LenderCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Register a new lender/money-lender."""
    existing = db.query(Lender).filter(Lender.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Lender with this email already exists")

    lender = Lender(
        name=data.name,
        email=data.email,
        phone=data.phone,
        organization=data.organization,
        lender_type=data.lender_type,
    )
    db.add(lender)
    db.commit()
    db.refresh(lender)
    return LenderResponse(
        id=lender.id, name=lender.name, email=lender.email,
        phone=lender.phone, organization=lender.organization,
        lender_type=lender.lender_type,
        created_at=lender.created_at.isoformat() if lender.created_at else None,
    )


@router.get("/lenders", response_model=List[LenderResponse])
def list_lenders(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all registered lenders."""
    lenders = db.query(Lender).order_by(Lender.id.desc()).all()
    return [LenderResponse(
        id=l.id, name=l.name, email=l.email, phone=l.phone,
        organization=l.organization, lender_type=l.lender_type,
        created_at=l.created_at.isoformat() if l.created_at else None,
    ) for l in lenders]


# ═══════════════════════════════════════════════
#  LISTING ENDPOINTS (Vendor side)
# ═══════════════════════════════════════════════

@router.post("/list/{invoice_id}", status_code=201)
def list_invoice_on_marketplace(
    invoice_id: int,
    listing_title: Optional[str] = FastForm(None),
    listing_description: Optional[str] = FastForm(None),
    requested_percentage: float = FastForm(80),
    discount_rate: Optional[float] = FastForm(None),
    max_interest_rate: float = FastForm(...),
    repayment_period_days: int = FastForm(...),
    images: List[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Vendor lists an invoice for financing on the marketplace."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # ── Vendor ownership check ──
    if current_user.role == "vendor" and invoice.vendor_id != current_user.vendor_id:
        raise HTTPException(status_code=403, detail="You can only list your own invoices")

    if invoice.is_listed:
        raise HTTPException(status_code=400, detail="Invoice is already listed on marketplace")

    if invoice.invoice_status == "cancelled":
        raise HTTPException(status_code=400, detail="Cannot list a cancelled invoice")

    if invoice.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Cannot list a fully paid invoice")

    # ── OCR verification required — no manual bills allowed ──
    if not invoice.source or invoice.source not in ("ocr_upload", "telegram"):
        raise HTTPException(
            status_code=400,
            detail="Only OCR-verified invoices can be listed on the marketplace. Please upload your invoice document (image/PDF) through the OCR upload feature to prevent fraud."
        )
    if invoice.ocr_status != "ocr_done":
        if invoice.ocr_status == "processing":
            raise HTTPException(status_code=400, detail="OCR is still processing this invoice. Please wait and try again.")
        elif invoice.ocr_status == "failed":
            raise HTTPException(status_code=400, detail="OCR failed for this invoice. Please re-upload a clearer image.")
        else:
            raise HTTPException(status_code=400, detail="Invoice has not been verified by OCR. Please upload the invoice document first.")

    # ── Vendor blacklist check ──
    vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first()
    if vendor and getattr(vendor, 'blacklisted', False):
        raise HTTPException(status_code=403, detail="Your account has been blacklisted due to payment defaults. You cannot list invoices.")

    if vendor and vendor.profile_status in ("suspended", "blacklisted"):
        raise HTTPException(status_code=403, detail=f"Your account is {vendor.profile_status}. Contact admin to resolve.")

    # ── Double-listing protection: check ALL active statuses ──
    existing = db.query(MarketplaceListing).filter(
        MarketplaceListing.invoice_id == invoice_id,
        MarketplaceListing.listing_status.in_(["open", "partially_funded", "funded"]),
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Invoice already has an active listing (status: {existing.listing_status})")

    vendor = db.query(Vendor).filter(Vendor.id == invoice.vendor_id).first()
    requested_amount = round(invoice.grand_total * requested_percentage / 100, 2)

    # ── Handle optional image uploads ──
    if images and images[0].filename:  # File(None) can give a single empty UploadFile
        upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
        os.makedirs(upload_dir, exist_ok=True)
        existing_images = []
        if vendor and vendor.business_images:
            try:
                existing_images = json.loads(vendor.business_images) if isinstance(vendor.business_images, str) else vendor.business_images
            except Exception:
                existing_images = []
        for img_file in images:
            if not img_file.filename:
                continue
            ext = os.path.splitext(img_file.filename)[1] or ".jpg"
            safe_name = f"{uuid.uuid4().hex}{ext}"
            file_path = os.path.join(upload_dir, safe_name)
            with open(file_path, "wb") as f:
                f.write(img_file.file.read())
            existing_images.append(f"/uploads/{safe_name}")
        if vendor:
            vendor.business_images = json.dumps(existing_images)

    # Generate invoice PDF, hash it, store hash on blockchain
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice_id).order_by(InvoiceItem.item_number).all()
    pdf_bytes = generate_invoice_pdf(invoice, vendor, items)
    pdf_hash = hashlib.sha256(pdf_bytes).hexdigest()

    listing = MarketplaceListing(
        invoice_id=invoice_id,
        vendor_id=invoice.vendor_id,
        listing_title=listing_title,
        listing_description=listing_description,
        requested_percentage=requested_percentage,
        requested_amount=requested_amount,
        discount_rate=discount_rate,
        max_interest_rate=max_interest_rate,
        repayment_period_days=repayment_period_days,
        listing_status="open",
        risk_score=vendor.risk_score if vendor else None,
        pdf_hash=pdf_hash,
    )

    # Record on blockchain
    block_data = {
        "type": "marketplace_listing",
        "invoice_id": invoice_id,
        "invoice_number": invoice.invoice_number,
        "vendor_id": invoice.vendor_id,
        "vendor_gstin": vendor.gstin if vendor else "",
        "grand_total": invoice.grand_total,
        "requested_percentage": requested_percentage,
        "requested_amount": requested_amount,
        "max_interest_rate": max_interest_rate,
        "repayment_period_days": repayment_period_days,
        "pdf_hash": pdf_hash,
        "listed_at": datetime.now(timezone.utc).isoformat(),
    }
    block = add_block(db, "listing", block_data)
    listing.blockchain_hash = block.block_hash

    invoice.is_listed = True
    invoice.listed_at = datetime.now(timezone.utc)

    db.add(listing)
    db.commit()
    db.refresh(listing)

    return {
        "message": "Invoice listed on marketplace",
        "listing_id": listing.id,
        "requested_amount": requested_amount,
        "max_interest_rate": max_interest_rate,
        "repayment_period_days": repayment_period_days,
        "blockchain_hash": block.block_hash,
        "pdf_hash": pdf_hash,
        "block_index": block.block_index,
    }


# ═══════════════════════════════════════════════
#  BROWSE / DETAIL ENDPOINTS (Lender side)
# ═══════════════════════════════════════════════

@router.get("/listings", response_model=List[MarketplaceBrowseItem])
def browse_listings(
    status: Optional[str] = None,
    amount_min: Optional[float] = None,
    amount_max: Optional[float] = None,
    interest_min: Optional[float] = None,
    interest_max: Optional[float] = None,
    risk_level: Optional[str] = None,  # low, medium, high
    business_type: Optional[str] = None,
    sort_by: Optional[str] = "created_at",  # amount, interest, risk, created_at
    sort_order: Optional[str] = "desc",  # asc, desc
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lender browses marketplace with advanced filters."""
    query = db.query(MarketplaceListing)
    if status:
        query = query.filter(MarketplaceListing.listing_status == status)
    if amount_min is not None:
        query = query.filter(MarketplaceListing.requested_amount >= amount_min)
    if amount_max is not None:
        query = query.filter(MarketplaceListing.requested_amount <= amount_max)
    if interest_min is not None:
        query = query.filter(MarketplaceListing.max_interest_rate >= interest_min)
    if interest_max is not None:
        query = query.filter(MarketplaceListing.max_interest_rate <= interest_max)
    if risk_level:
        if risk_level == "low":
            query = query.filter(MarketplaceListing.risk_score <= 30)
        elif risk_level == "medium":
            query = query.filter(MarketplaceListing.risk_score > 30, MarketplaceListing.risk_score <= 60)
        elif risk_level == "high":
            query = query.filter(MarketplaceListing.risk_score > 60)

    # Sort
    sort_map = {
        "amount": MarketplaceListing.requested_amount,
        "interest": MarketplaceListing.max_interest_rate,
        "risk": MarketplaceListing.risk_score,
        "created_at": MarketplaceListing.created_at,
    }
    sort_col = sort_map.get(sort_by, MarketplaceListing.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    listings = query.offset(skip).limit(limit).all()

    results = []
    for listing in listings:
        invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
        vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()

        # Apply business_type filter post-query (since it's on vendor table)
        if business_type and vendor and vendor.business_type != business_type:
            continue

        # Count total funded deals for this vendor
        total_funded = db.query(MarketplaceListing).filter(
            MarketplaceListing.vendor_id == listing.vendor_id,
            MarketplaceListing.listing_status.in_(["funded", "settled"]),
        ).count()

        # Parse business images JSON
        import json as _json
        biz_images = []
        if vendor and vendor.business_images:
            try:
                biz_images = _json.loads(vendor.business_images)
            except Exception:
                biz_images = []

        # Calculate risk score if not present
        risk = listing.risk_score
        if risk is None and vendor:
            risk = _compute_risk_score(vendor)
            listing.risk_score = risk
            db.commit()

        results.append(MarketplaceBrowseItem(
            id=listing.id,
            invoice_id=listing.invoice_id,
            listing_title=listing.listing_title,
            listing_description=listing.listing_description,
            vendor_name=vendor.full_name if vendor else "Unknown",
            business_name=vendor.business_name if vendor else "Unknown",
            business_type=vendor.business_type if vendor else None,
            business_category=vendor.business_category if vendor else None,
            business_description=vendor.business_description if vendor else None,
            business_city=vendor.business_city if vendor else None,
            business_state=vendor.business_state if vendor else None,
            business_images=biz_images,
            year_of_establishment=vendor.year_of_establishment if vendor else None,
            number_of_employees=vendor.number_of_employees if vendor else None,
            profile_status=vendor.profile_status if vendor else None,
            cibil_score=vendor.cibil_score if vendor else None,
            annual_turnover=vendor.annual_turnover if vendor else None,
            total_reviews=vendor.total_reviews if vendor else 0,
            average_rating=vendor.average_rating if vendor else 0.0,
            requested_amount=listing.requested_amount,
            max_interest_rate=listing.max_interest_rate,
            repayment_period_days=listing.repayment_period_days,
            listing_status=listing.listing_status,
            risk_score=risk,
            invoice_number=invoice.invoice_number if invoice else None,
            invoice_date=invoice.invoice_date if invoice else None,
            due_date=invoice.due_date if invoice else None,
            grand_total=invoice.grand_total if invoice else None,
            blockchain_hash=listing.blockchain_hash,
            created_at=listing.created_at.isoformat() if listing.created_at else None,
            funded_amount=listing.funded_amount,
            total_funded_deals=total_funded,
            # Community Pot fields
            total_funded_amount=listing.total_funded_amount or 0,
            total_investors=listing.total_investors or 0,
            min_investment=listing.min_investment or 500,
            funding_progress_pct=round((listing.total_funded_amount or 0) / listing.requested_amount * 100, 1) if listing.requested_amount > 0 else 0,
            remaining_amount=max(0, listing.requested_amount - (listing.total_funded_amount or 0)),
        ))

    return results


@router.get("/listings/{listing_id}", response_model=MarketplaceDetailItem)
def get_listing_detail(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Lender clicks on a listing — sees CIBIL, GST compliance, full details."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()

    # Count total funded deals for this vendor
    total_funded = db.query(MarketplaceListing).filter(
        MarketplaceListing.vendor_id == listing.vendor_id,
        MarketplaceListing.listing_status.in_(["funded", "settled"]),
    ).count()

    # Parse business images JSON
    import json as _json
    biz_images = []
    if vendor and vendor.business_images:
        try:
            biz_images = _json.loads(vendor.business_images)
        except Exception:
            biz_images = []

    # Calculate risk score if not present
    risk = listing.risk_score
    if risk is None and vendor:
        risk = _compute_risk_score(vendor)
        listing.risk_score = risk
        db.commit()

    # ── Fetch fractional investors for this listing ──
    frac_investments = db.query(FractionalInvestment).filter(
        FractionalInvestment.listing_id == listing.id,
        FractionalInvestment.status == "active",
    ).order_by(FractionalInvestment.invested_at.desc()).all()

    investors_list = []
    for fi in frac_investments:
        inv_lender = db.query(Lender).filter(Lender.id == fi.lender_id).first()
        investors_list.append({
            "id": fi.id,
            "lender_id": fi.lender_id,
            "lender_name": inv_lender.name if inv_lender else "Anonymous",
            "lender_type": inv_lender.lender_type if inv_lender else "individual",
            "organization": inv_lender.organization if inv_lender else None,
            "invested_amount": fi.invested_amount,
            "offered_interest_rate": fi.offered_interest_rate,
            "ownership_percentage": fi.ownership_percentage,
            "expected_return": fi.expected_return,
            "invested_at": fi.invested_at.isoformat() if fi.invested_at else None,
            "blockchain_hash": fi.blockchain_hash,
        })

    return MarketplaceDetailItem(
        id=listing.id,
        invoice_id=listing.invoice_id,
        vendor_id=listing.vendor_id,
        listing_title=listing.listing_title,
        listing_description=listing.listing_description,
        vendor_name=vendor.full_name if vendor else "Unknown",
        business_name=vendor.business_name if vendor else "Unknown",
        business_type=vendor.business_type if vendor else None,
        business_category=vendor.business_category if vendor else None,
        business_description=vendor.business_description if vendor else None,
        business_city=vendor.business_city if vendor else None,
        business_state=vendor.business_state if vendor else None,
        business_images=biz_images,
        year_of_establishment=vendor.year_of_establishment if vendor else None,
        number_of_employees=vendor.number_of_employees if vendor else None,
        vendor_gstin=vendor.gstin if vendor else None,
        vendor_state=vendor.business_state if vendor else None,
        profile_status=vendor.profile_status if vendor else None,
        cibil_score=vendor.cibil_score if vendor else None,
        annual_turnover=vendor.annual_turnover if vendor else None,
        monthly_revenue=vendor.monthly_revenue if vendor else None,
        risk_score=risk,
        existing_liabilities=vendor.existing_liabilities if vendor else None,
        total_reviews=vendor.total_reviews if vendor else 0,
        average_rating=vendor.average_rating if vendor else 0.0,
        total_funded_deals=total_funded,
        gst_filing_frequency=vendor.gst_filing_frequency if vendor else None,
        total_gst_filings=vendor.total_gst_filings if vendor else None,
        gst_compliance_status=vendor.gst_compliance_status if vendor else None,
        requested_percentage=listing.requested_percentage,
        requested_amount=listing.requested_amount,
        discount_rate=listing.discount_rate,
        max_interest_rate=listing.max_interest_rate,
        repayment_period_days=listing.repayment_period_days,
        listing_status=listing.listing_status,
        blockchain_hash=listing.blockchain_hash,
        pdf_hash=listing.pdf_hash,
        invoice_number=invoice.invoice_number if invoice else None,
        invoice_date=invoice.invoice_date if invoice else None,
        due_date=invoice.due_date if invoice else None,
        grand_total=invoice.grand_total if invoice else None,
        buyer_name=invoice.buyer_name if invoice else None,
        buyer_gstin=invoice.buyer_gstin if invoice else None,
        supply_type=invoice.supply_type if invoice else None,
        funded_amount=listing.funded_amount,
        funded_by=listing.funded_by,
        funded_at=listing.funded_at.isoformat() if listing.funded_at else None,
        # Community Pot fields
        total_funded_amount=listing.total_funded_amount or 0,
        total_investors=listing.total_investors or 0,
        min_investment=listing.min_investment or 500,
        funding_progress_pct=round((listing.total_funded_amount or 0) / listing.requested_amount * 100, 1) if listing.requested_amount > 0 else 0,
        remaining_amount=max(0, listing.requested_amount - (listing.total_funded_amount or 0)),
        investors=investors_list,
        created_at=listing.created_at.isoformat() if listing.created_at else None,
    )


# ═══════════════════════════════════════════════
#  INVOICE PDF (Blockchain-secured)
# ═══════════════════════════════════════════════

@router.get("/listings/{listing_id}/invoice-pdf")
def request_invoice_pdf(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Lender requests the invoice PDF.
    - Regenerates PDF from DB
    - Verifies hash against blockchain-stored hash (integrity check)
    - Returns the decrypted/verified PDF
    """
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()
    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == listing.invoice_id).order_by(InvoiceItem.item_number).all()

    if not invoice or not vendor:
        raise HTTPException(status_code=404, detail="Invoice or vendor not found")

    # Regenerate PDF
    pdf_bytes = generate_invoice_pdf(invoice, vendor, items)
    current_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # Verify against stored blockchain hash
    integrity_ok = (current_hash == listing.pdf_hash) if listing.pdf_hash else True

    # Record PDF access on blockchain
    block_data = {
        "type": "pdf_access",
        "listing_id": listing_id,
        "invoice_number": invoice.invoice_number,
        "pdf_hash": current_hash,
        "integrity_verified": integrity_ok,
        "accessed_at": datetime.now(timezone.utc).isoformat(),
    }
    add_block(db, "pdf_access", block_data)
    db.commit()

    if not integrity_ok:
        raise HTTPException(status_code=422, detail="PDF integrity check failed — invoice data may have been tampered with")

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"inline; filename={invoice.invoice_number}.pdf",
            "X-Blockchain-Hash": listing.blockchain_hash or "",
            "X-PDF-Hash": current_hash,
            "X-Integrity-Verified": str(integrity_ok),
        },
    )


@router.get("/listings/{listing_id}/gst-filings")
def request_gst_filings(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Lender requests vendor's GST filing info for due diligence."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # Record GST filing request on blockchain
    block_data = {
        "type": "gst_filing_request",
        "listing_id": listing_id,
        "vendor_id": vendor.id,
        "vendor_gstin": vendor.gstin,
        "requested_at": datetime.now(timezone.utc).isoformat(),
    }
    add_block(db, "gst_request", block_data)
    db.commit()

    return {
        "vendor_name": vendor.full_name,
        "business_name": vendor.business_name,
        "gstin": vendor.gstin,
        "gst_registration_date": vendor.gst_registration_date,
        "gst_filing_frequency": vendor.gst_filing_frequency,
        "total_gst_filings": vendor.total_gst_filings,
        "gst_compliance_status": vendor.gst_compliance_status,
        "blockchain_recorded": True,
    }


# ═══════════════════════════════════════════════
#  FUNDING / SETTLEMENT
# ═══════════════════════════════════════════════

@router.post("/fund/{listing_id}")
def fund_listing(listing_id: int, data: FundListingRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Fractional / Community Pot funding — any lender can fund a *slice* of an invoice.
    Multiple investors can fund pieces until the listing is fully funded.
    """
    # Only lenders can fund listings
    if current_user.role != "lender":
        raise HTTPException(status_code=403, detail="Only lenders can fund marketplace listings")

    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.listing_status not in ("open", "partially_funded"):
        raise HTTPException(status_code=400, detail=f"Listing is '{listing.listing_status}', not open for funding")

    remaining = listing.requested_amount - (listing.total_funded_amount or 0)
    if data.funded_amount > remaining + 0.01:  # small float tolerance
        raise HTTPException(status_code=400, detail=f"Amount ₹{data.funded_amount:,.0f} exceeds remaining ₹{remaining:,.0f}")

    min_inv = listing.min_investment or 500
    if data.funded_amount < min_inv and data.funded_amount < remaining:
        raise HTTPException(status_code=400, detail=f"Minimum investment is ₹{min_inv:,.0f}")

    if data.offered_interest_rate > listing.max_interest_rate:
        raise HTTPException(status_code=400, detail=f"Offered interest rate ({data.offered_interest_rate}%) exceeds vendor's max ({listing.max_interest_rate}%)")

    lender = db.query(Lender).filter(Lender.id == data.lender_id).first()
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")

    # ── Self-funding check: vendor cannot fund their own listing ──
    if current_user.vendor_id and current_user.vendor_id == listing.vendor_id:
        raise HTTPException(status_code=403, detail="Vendors cannot fund their own listings")

    # ── Wallet balance check & escrow lock ──
    if lender.wallet_balance < data.funded_amount:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient wallet balance. Available: ₹{lender.wallet_balance:,.0f}, Required: ₹{data.funded_amount:,.0f}. Please top-up your wallet first.",
        )

    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()

    # ── Create FractionalInvestment record ──
    ownership_pct = round((data.funded_amount / listing.requested_amount) * 100, 2)
    expected_return = round((data.funded_amount * data.offered_interest_rate / 100) * (listing.repayment_period_days / 365), 2)

    block_data = {
        "type": "fractional_funding",
        "listing_id": listing_id,
        "invoice_number": invoice.invoice_number if invoice else "",
        "lender_id": lender.id,
        "lender_name": lender.name,
        "funded_amount": data.funded_amount,
        "ownership_pct": ownership_pct,
        "offered_interest_rate": data.offered_interest_rate,
        "funded_at": datetime.now(timezone.utc).isoformat(),
    }
    block = add_block(db, "funding", block_data)

    frac = FractionalInvestment(
        listing_id=listing_id,
        lender_id=lender.id,
        user_id=current_user.id,
        invested_amount=data.funded_amount,
        offered_interest_rate=data.offered_interest_rate,
        ownership_percentage=ownership_pct,
        expected_return=expected_return,
        blockchain_hash=block.block_hash,
        status="active",
    )
    db.add(frac)
    db.flush()  # Ensure fractional investment is queryable for weighted avg calc

    # ── Wallet: deduct from available, lock in escrow ──
    lender.wallet_balance = round(lender.wallet_balance - data.funded_amount, 2)
    lender.escrow_locked = round((lender.escrow_locked or 0) + data.funded_amount, 2)
    lender.total_invested = round((lender.total_invested or 0) + data.funded_amount, 2)

    # ── Update listing aggregates ──
    new_total = (listing.total_funded_amount or 0) + data.funded_amount
    listing.total_funded_amount = round(new_total, 2)
    listing.total_investors = (listing.total_investors or 0) + 1

    # Check if listing is now fully funded
    fully_funded = new_total >= listing.requested_amount - 0.01
    if fully_funded:
        listing.listing_status = "funded"
        listing.funded_amount = round(new_total, 2)
        listing.funded_at = datetime.now(timezone.utc)
        # For backwards compat, set lender_id to last funder if single investor
        if listing.total_investors == 1:
            listing.lender_id = lender.id
            listing.funded_by = lender.name
        else:
            listing.funded_by = f"{listing.total_investors} investors"

        # ── Generate repayment schedule (weighted average rate) ──
        all_fracs = db.query(FractionalInvestment).filter(
            FractionalInvestment.listing_id == listing_id,
            FractionalInvestment.status == "active",
        ).all()
        # Weighted average interest rate across all investors
        total_weighted_rate = sum(f.invested_amount * f.offered_interest_rate for f in all_fracs)
        avg_rate = total_weighted_rate / new_total if new_total > 0 else data.offered_interest_rate

        num_installments = max(1, listing.repayment_period_days // 30)
        principal_per = round(new_total / num_installments, 2)
        annual_rate = avg_rate / 100
        remaining_principal = new_total
        for i in range(1, num_installments + 1):
            due = datetime.now(timezone.utc) + timedelta(days=30 * i)
            # Declining balance: interest on remaining principal
            interest_amt = round((remaining_principal * annual_rate * 30) / 365, 2)
            remaining_principal = max(0, remaining_principal - principal_per)
            sched = RepaymentSchedule(
                listing_id=listing_id,
                installment_number=i,
                due_date=due.strftime("%Y-%m-%d"),
                principal_amount=principal_per,
                interest_amount=interest_amt,
                total_amount=round(principal_per + interest_amt, 2),
                status="pending",
            )
            db.add(sched)

        # ── Create Time-Lock release schedule (anti hit-and-run) ──
        create_timelock_schedule(db, listing_id, listing.vendor_id, new_total, listing.funded_at)

        # Notify vendor — fully funded
        vendor_user = db.query(User).filter(User.vendor_id == listing.vendor_id).first()
        if vendor_user:
            db.add(Notification(
                user_id=vendor_user.id,
                title="Invoice Fully Funded! 🎉",
                message=f"Your invoice has been fully funded ₹{new_total:,.0f} by {listing.total_investors} investor(s). Repayment in {num_installments} installments.",
                notification_type="funding",
                link=f"/vendor/{listing.vendor_id}/invoices",
            ))
    else:
        listing.listing_status = "partially_funded"
        # Notify vendor — partial funding
        vendor_user = db.query(User).filter(User.vendor_id == listing.vendor_id).first()
        if vendor_user:
            pct = round(new_total / listing.requested_amount * 100, 1)
            db.add(Notification(
                user_id=vendor_user.id,
                title="New Investment Received! 💰",
                message=f"{lender.name} invested ₹{data.funded_amount:,.0f} in your invoice ({pct}% funded, {listing.total_investors} investor(s)).",
                notification_type="funding",
                link=f"/vendor/{listing.vendor_id}/invoices",
            ))

    # Notify lender
    lender_user = db.query(User).filter(User.lender_id == lender.id).first()
    if lender_user:
        db.add(Notification(
            user_id=lender_user.id,
            title="Investment Confirmed ✅",
            message=f"You invested ₹{data.funded_amount:,.0f} ({ownership_pct}% ownership) in invoice {invoice.invoice_number if invoice else ''}. Expected return: ₹{expected_return:,.0f}.",
            notification_type="funding",
            link=f"/marketplace/{listing_id}",
        ))

    # ── Log activity ──
    import json as json_mod
    db.add(ActivityLog(
        entity_type="listing", entity_id=listing_id,
        action="fractional_funded",
        description=f"₹{data.funded_amount:,.0f} invested by {lender.name} ({ownership_pct}% slice) at {data.offered_interest_rate}%",
        metadata_json=json_mod.dumps({
            "lender_id": lender.id,
            "amount": data.funded_amount,
            "ownership_pct": ownership_pct,
            "total_funded": new_total,
            "total_investors": listing.total_investors,
        }),
    ))

    # ── Trigger credit score recalculation on funding event ──
    try:
        from services.credit_scoring import compute_credit_score
        compute_credit_score(db, listing.vendor_id)
    except Exception:
        pass  # Non-critical — don't fail the funding

    db.commit()
    return {
        "message": "Investment recorded successfully" if not fully_funded else "Listing fully funded!",
        "invested_amount": data.funded_amount,
        "ownership_percentage": ownership_pct,
        "expected_return": expected_return,
        "lender": lender.name,
        "blockchain_hash": block.block_hash,
        "total_funded_amount": listing.total_funded_amount,
        "total_investors": listing.total_investors,
        "funding_progress_pct": round(new_total / listing.requested_amount * 100, 1),
        "remaining_amount": max(0, listing.requested_amount - new_total),
        "fully_funded": fully_funded,
    }


# ═══════════════════════════════════════════════
#  COMMUNITY POT — INVESTOR ENDPOINTS
# ═══════════════════════════════════════════════

@router.get("/listings/{listing_id}/investors")
def get_listing_investors(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all fractional investors for a listing."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    investments = db.query(FractionalInvestment).filter(
        FractionalInvestment.listing_id == listing_id,
        FractionalInvestment.status == "active",
    ).order_by(FractionalInvestment.invested_at.desc()).all()

    investors = []
    for fi in investments:
        inv_lender = db.query(Lender).filter(Lender.id == fi.lender_id).first()
        investors.append({
            "id": fi.id,
            "lender_id": fi.lender_id,
            "lender_name": inv_lender.name if inv_lender else "Anonymous",
            "lender_type": inv_lender.lender_type if inv_lender else "individual",
            "organization": inv_lender.organization if inv_lender else None,
            "invested_amount": fi.invested_amount,
            "offered_interest_rate": fi.offered_interest_rate,
            "ownership_percentage": fi.ownership_percentage,
            "expected_return": fi.expected_return,
            "invested_at": fi.invested_at.isoformat() if fi.invested_at else None,
            "blockchain_hash": fi.blockchain_hash,
            "status": fi.status,
        })

    return {
        "listing_id": listing_id,
        "total_funded_amount": listing.total_funded_amount or 0,
        "total_investors": listing.total_investors or 0,
        "requested_amount": listing.requested_amount,
        "funding_progress_pct": round((listing.total_funded_amount or 0) / listing.requested_amount * 100, 1) if listing.requested_amount > 0 else 0,
        "remaining_amount": max(0, listing.requested_amount - (listing.total_funded_amount or 0)),
        "investors": investors,
    }


@router.get("/listings/{listing_id}/funding-progress")
def get_funding_progress(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Quick endpoint for funding progress (for live updates)."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    return {
        "listing_id": listing_id,
        "listing_status": listing.listing_status,
        "requested_amount": listing.requested_amount,
        "total_funded_amount": listing.total_funded_amount or 0,
        "total_investors": listing.total_investors or 0,
        "funding_progress_pct": round((listing.total_funded_amount or 0) / listing.requested_amount * 100, 1) if listing.requested_amount > 0 else 0,
        "remaining_amount": max(0, listing.requested_amount - (listing.total_funded_amount or 0)),
        "min_investment": listing.min_investment or 500,
    }


@router.post("/settle/{listing_id}")
def settle_listing(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Mark a listing as settled."""
    # Only admin or the vendor who owns the listing can settle
    if current_user.role not in ("admin",):
        if current_user.role == "vendor":
            listing_check = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
            if not listing_check or listing_check.vendor_id != current_user.vendor_id:
                raise HTTPException(status_code=403, detail="Not authorized to settle this listing")
        else:
            raise HTTPException(status_code=403, detail="Only vendors or admins can settle listings")

    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.listing_status != "funded":
        raise HTTPException(status_code=400, detail="Only funded listings can be settled")

    listing.listing_status = "settled"
    listing.settlement_date = datetime.now(timezone.utc)

    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
    if invoice:
        invoice.payment_status = "paid"
        invoice.invoice_status = "paid"

    block_data = {
        "type": "settlement",
        "listing_id": listing_id,
        "invoice_number": invoice.invoice_number if invoice else "",
        "settled_at": datetime.now(timezone.utc).isoformat(),
    }
    add_block(db, "settlement", block_data)

    # ── Trigger credit score recalculation on settlement ──
    try:
        from services.credit_scoring import compute_credit_score
        compute_credit_score(db, listing.vendor_id)
    except Exception:
        pass

    db.commit()
    return {"message": "Listing settled successfully"}


# ═══════════════════════════════════════════════
#  SMART CONTRACT PDF
# ═══════════════════════════════════════════════

@router.get("/listings/{listing_id}/smart-contract-pdf")
def download_smart_contract_pdf(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Download a comprehensive Smart Contract PDF for a settled/funded listing."""
    from smart_contract_pdf import generate_smart_contract_pdf

    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    if listing.listing_status not in ("funded", "settled"):
        raise HTTPException(status_code=400, detail="Smart contract is only available for funded or settled listings")

    invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    vendor = db.query(Vendor).filter(Vendor.id == listing.vendor_id).first()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    # For Community Pot listings, lender_id may be None — use the first/largest investor
    lender = None
    if listing.lender_id:
        lender = db.query(Lender).filter(Lender.id == listing.lender_id).first()
    if not lender:
        # Fallback: get the largest fractional investor
        frac = db.query(FractionalInvestment).filter(
            FractionalInvestment.listing_id == listing_id
        ).order_by(FractionalInvestment.invested_amount.desc()).first()
        if frac:
            lender = db.query(Lender).filter(Lender.id == frac.lender_id).first()
    if not lender:
        raise HTTPException(status_code=400, detail="No lender found for this listing")

    items = db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).order_by(InvoiceItem.item_number).all()
    repayments = db.query(RepaymentSchedule).filter(RepaymentSchedule.listing_id == listing_id).order_by(RepaymentSchedule.installment_number).all()

    pdf_bytes = generate_smart_contract_pdf(
        listing=listing,
        invoice=invoice,
        vendor=vendor,
        lender=lender,
        items=items,
        repayments=repayments,
    )

    filename = f"SmartContract_SC-{listing.id:04d}_{invoice.invoice_number}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═══════════════════════════════════════════════
#  VENDOR REPAYMENTS (aggregated view)
# ═══════════════════════════════════════════════

@router.get("/vendor-repayments/{vendor_id}")
def get_vendor_repayments(vendor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get all repayment schedules for a vendor's funded/settled listings."""
    # Get all listings for this vendor that have repayment schedules
    listings = db.query(MarketplaceListing).filter(
        MarketplaceListing.vendor_id == vendor_id,
        MarketplaceListing.listing_status.in_(["funded", "settled"]),
    ).all()

    result = []
    for listing in listings:
        schedules = db.query(RepaymentSchedule).filter(
            RepaymentSchedule.listing_id == listing.id
        ).order_by(RepaymentSchedule.installment_number).all()

        if not schedules:
            continue

        invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()

        total_due = sum(s.total_amount for s in schedules)
        total_paid = sum(s.paid_amount or 0 for s in schedules if s.status == "paid")
        remaining = total_due - total_paid

        result.append({
            "listing_id": listing.id,
            "invoice_number": invoice.invoice_number if invoice else "N/A",
            "buyer_name": invoice.buyer_name if invoice else "N/A",
            "listing_status": listing.listing_status,
            "funded_amount": listing.funded_amount,
            "interest_rate": listing.max_interest_rate,
            "total_due": total_due,
            "total_paid": total_paid,
            "remaining": remaining,
            "installments": [{
                "id": s.id,
                "installment_number": s.installment_number,
                "due_date": s.due_date,
                "principal_amount": s.principal_amount,
                "interest_amount": s.interest_amount,
                "total_amount": s.total_amount,
                "status": s.status,
                "paid_date": s.paid_date,
                "paid_amount": s.paid_amount,
            } for s in schedules],
        })

    return result


# ═══════════════════════════════════════════════
#  BLOCKCHAIN ENDPOINTS
# ═══════════════════════════════════════════════

@router.get("/blockchain/validate")
def validate_blockchain(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return validate_chain(db)


@router.get("/blockchain/blocks")
def get_blockchain_blocks(limit: int = 50, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    blocks = db.query(BlockchainBlock).order_by(BlockchainBlock.block_index.desc()).limit(limit).all()
    return [
        {
            "block_index": b.block_index,
            "data_type": b.data_type,
            "data_hash": b.data_hash,
            "block_hash": b.block_hash,
            "previous_hash": b.previous_hash,
            "nonce": b.nonce,
            "timestamp": b.timestamp.isoformat() if b.timestamp else None,
        }
        for b in blocks
    ]


# ═══════════════════════════════════════════════
#  REPAYMENT SCHEDULE
# ═══════════════════════════════════════════════

@router.get("/listings/{listing_id}/repayment")
def get_repayment_schedule(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the repayment schedule for a funded listing."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    schedules = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.listing_id == listing_id
    ).order_by(RepaymentSchedule.installment_number).all()

    return {
        "listing_id": listing_id,
        "listing_status": listing.listing_status,
        "funded_amount": listing.funded_amount,
        "total_installments": len(schedules),
        "installments": [{
            "id": s.id,
            "installment_number": s.installment_number,
            "due_date": s.due_date,
            "principal_amount": s.principal_amount,
            "interest_amount": s.interest_amount,
            "total_amount": s.total_amount,
            "status": s.status,
            "paid_date": s.paid_date,
            "paid_amount": s.paid_amount,
        } for s in schedules],
    }


@router.post("/listings/{listing_id}/repayment/{installment_id}/pay")
def pay_installment(listing_id: int, installment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Record payment of a repayment installment."""
    # Only the vendor who owns the listing or admin can pay
    listing_owner = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if listing_owner and current_user.role == "vendor" and listing_owner.vendor_id != current_user.vendor_id:
        raise HTTPException(status_code=403, detail="Not authorized to pay this installment")
    if current_user.role not in ("vendor", "admin"):
        raise HTTPException(status_code=403, detail="Only vendors or admins can pay installments")

    sched = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.id == installment_id,
        RepaymentSchedule.listing_id == listing_id,
    ).first()
    if not sched:
        raise HTTPException(status_code=404, detail="Installment not found")

    if sched.status == "paid":
        raise HTTPException(status_code=400, detail="Already paid")

    sched.status = "paid"
    sched.paid_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sched.paid_amount = sched.total_amount

    # Record on blockchain
    block_data = {
        "type": "repayment",
        "listing_id": listing_id,
        "installment": sched.installment_number,
        "amount": sched.total_amount,
        "paid_at": datetime.now(timezone.utc).isoformat(),
    }
    add_block(db, "repayment", block_data)

    # Check if all installments are paid → auto-settle
    remaining = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.listing_id == listing_id,
        RepaymentSchedule.status != "paid",
    ).count()

    if remaining == 0:
        listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
        if listing and listing.listing_status == "funded":
            listing.listing_status = "settled"
            listing.settlement_date = datetime.now(timezone.utc)
            invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
            if invoice:
                invoice.payment_status = "paid"
                invoice.invoice_status = "paid"
            add_block(db, "settlement", {
                "type": "auto_settlement",
                "listing_id": listing_id,
                "settled_at": datetime.now(timezone.utc).isoformat(),
            })

    # ── Trigger credit score recalculation on repayment event ──
    listing_for_rescore = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if listing_for_rescore:
        try:
            from services.credit_scoring import compute_credit_score
            compute_credit_score(db, listing_for_rescore.vendor_id)
        except Exception:
            pass

    db.commit()
    return {"message": f"Installment #{sched.installment_number} paid", "remaining": remaining}


# ═══════════════════════════════════════════════
#  LENDER WALLET ENDPOINTS
# ═══════════════════════════════════════════════

class WalletTopUpRequest(BaseModel):
    lender_id: int
    amount: float = Field(..., gt=0, description="Amount to add to wallet (₹)")

@router.get("/lender/{lender_id}/wallet")
def get_lender_wallet(lender_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get lender wallet balance and summary."""
    lender = db.query(Lender).filter(Lender.id == lender_id).first()
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")

    # Count active investments
    active_investments = db.query(FractionalInvestment).filter(
        FractionalInvestment.lender_id == lender_id,
        FractionalInvestment.status == "active",
    ).count()

    return {
        "lender_id": lender_id,
        "lender_name": lender.name,
        "wallet_balance": lender.wallet_balance,
        "escrow_locked": lender.escrow_locked or 0,
        "total_invested": lender.total_invested or 0,
        "total_returns": lender.total_returns or 0,
        "active_investments": active_investments,
        "net_worth": round((lender.wallet_balance or 0) + (lender.escrow_locked or 0), 2),
    }

@router.post("/lender/wallet/topup")
def topup_lender_wallet(data: WalletTopUpRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Add funds to lender's wallet (simulated bank transfer)."""
    if current_user.role not in ("lender", "admin"):
        raise HTTPException(status_code=403, detail="Only lenders or admins can top-up wallets")

    lender = db.query(Lender).filter(Lender.id == data.lender_id).first()
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")

    lender.wallet_balance = round((lender.wallet_balance or 0) + data.amount, 2)

    db.add(ActivityLog(
        entity_type="lender", entity_id=lender.id,
        action="wallet_topup",
        description=f"Wallet topped up by ₹{data.amount:,.0f}. New balance: ₹{lender.wallet_balance:,.0f}",
    ))

    db.add(Notification(
        user_id=current_user.id,
        title="Wallet Top-Up ✅",
        message=f"₹{data.amount:,.0f} added to your wallet. Balance: ₹{lender.wallet_balance:,.0f}",
        notification_type="wallet",
    ))

    db.commit()
    return {
        "message": f"₹{data.amount:,.0f} added to wallet",
        "new_balance": lender.wallet_balance,
        "escrow_locked": lender.escrow_locked or 0,
    }


class WalletWithdrawRequest(BaseModel):
    lender_id: int
    amount: float = Field(..., gt=0, description="Amount to withdraw (₹)")
    bank_account: Optional[str] = None


@router.post("/lender/wallet/withdraw")
def withdraw_from_wallet(data: WalletWithdrawRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Withdraw available balance from lender's wallet to bank account."""
    if current_user.role not in ("lender", "admin"):
        raise HTTPException(status_code=403, detail="Only lenders can withdraw")

    lender = db.query(Lender).filter(Lender.id == data.lender_id).first()
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")

    available = lender.wallet_balance or 0
    if data.amount > available:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance. Available: ₹{available:,.2f}, Requested: ₹{data.amount:,.2f}"
        )

    lender.wallet_balance = round(available - data.amount, 2)
    lender.total_withdrawn = round((getattr(lender, 'total_withdrawn', 0) or 0) + data.amount, 2)

    # Record on blockchain
    block_data = {
        "type": "withdrawal",
        "lender_id": lender.id,
        "amount": data.amount,
        "remaining_balance": lender.wallet_balance,
        "withdrawn_at": datetime.now(timezone.utc).isoformat(),
    }
    block = add_block(db, "withdrawal", block_data)

    db.add(ActivityLog(
        entity_type="lender", entity_id=lender.id,
        action="withdrawal",
        description=f"₹{data.amount:,.0f} withdrawn to bank. Remaining: ₹{lender.wallet_balance:,.0f}",
    ))

    db.add(Notification(
        user_id=current_user.id,
        title="Withdrawal Processed ✅",
        message=f"₹{data.amount:,.0f} has been withdrawn. Remaining balance: ₹{lender.wallet_balance:,.0f}",
        notification_type="wallet",
    ))

    db.commit()
    return {
        "message": f"₹{data.amount:,.0f} withdrawn successfully",
        "withdrawn_amount": data.amount,
        "new_balance": lender.wallet_balance,
        "escrow_locked": lender.escrow_locked or 0,
        "blockchain_hash": block.block_hash,
    }


# ═══════════════════════════════════════════════
#  TIME-LOCK RELEASE ENDPOINTS
# ═══════════════════════════════════════════════

# Time-lock tranches: prevents hit-and-run by releasing funds in stages
TIMELOCK_TRANCHES = [
    {"tranche": 1, "day": 0,  "pct": 50},   # Day 0:  50% released immediately
    {"tranche": 2, "day": 7,  "pct": 20},   # Day 7:  20% released
    {"tranche": 3, "day": 14, "pct": 15},   # Day 14: 15% released
    {"tranche": 4, "day": 30, "pct": 15},   # Day 30: 15% released (final)
]


def create_timelock_schedule(db: Session, listing_id: int, vendor_id: int, total_amount: float, funded_at: datetime):
    """Create time-lock release tranches for a newly funded listing."""
    for t in TIMELOCK_TRANCHES:
        release_date = (funded_at + timedelta(days=t["day"])).strftime("%Y-%m-%d")
        amount = round(total_amount * t["pct"] / 100, 2)
        # Day 0 tranche is released immediately
        status = "released" if t["day"] == 0 else "locked"
        released_at_val = funded_at if t["day"] == 0 else None

        tl = TimeLockRelease(
            listing_id=listing_id,
            vendor_id=vendor_id,
            tranche_number=t["tranche"],
            release_day=t["day"],
            release_date=release_date,
            release_percentage=t["pct"],
            release_amount=amount,
            status=status,
            released_at=released_at_val,
        )
        db.add(tl)

    # Record on blockchain
    block = add_block(db, "timelock_created", {
        "type": "timelock_schedule",
        "listing_id": listing_id,
        "vendor_id": vendor_id,
        "total_amount": total_amount,
        "tranches": TIMELOCK_TRANCHES,
        "created_at": funded_at.isoformat(),
    })

    return block


@router.get("/listings/{listing_id}/timelock")
def get_timelock_schedule(listing_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get time-lock release schedule for a listing."""
    listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    releases = db.query(TimeLockRelease).filter(
        TimeLockRelease.listing_id == listing_id
    ).order_by(TimeLockRelease.tranche_number).all()

    # Auto-release eligible tranches
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    released_now = []
    for r in releases:
        if r.status == "locked" and r.release_date <= today:
            r.status = "released"
            r.released_at = datetime.now(timezone.utc)
            released_now.append(r.tranche_number)
            # Blockchain record
            add_block(db, "timelock_release", {
                "type": "timelock_tranche_released",
                "listing_id": listing_id,
                "tranche": r.tranche_number,
                "amount": r.release_amount,
                "release_day": r.release_day,
                "released_at": datetime.now(timezone.utc).isoformat(),
            })
    if released_now:
        db.commit()

    total_amount = sum(r.release_amount for r in releases)
    released_amount = sum(r.release_amount for r in releases if r.status == "released")
    locked_amount = total_amount - released_amount

    return {
        "listing_id": listing_id,
        "total_amount": total_amount,
        "released_amount": released_amount,
        "locked_amount": locked_amount,
        "tranches": [{
            "tranche_number": r.tranche_number,
            "release_day": r.release_day,
            "release_date": r.release_date,
            "release_percentage": r.release_percentage,
            "release_amount": r.release_amount,
            "status": r.status,
            "released_at": r.released_at.isoformat() if r.released_at else None,
        } for r in releases],
    }


@router.get("/lender/{lender_id}/withdrawable")
def get_withdrawable_balance(lender_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get lender's withdrawable balance (wallet balance from settled+released funds)."""
    lender = db.query(Lender).filter(Lender.id == lender_id).first()
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")

    # Get all settled investments for this lender
    settled = db.query(FractionalInvestment).filter(
        FractionalInvestment.lender_id == lender_id,
        FractionalInvestment.status == "settled",
    ).all()

    return {
        "wallet_balance": lender.wallet_balance or 0,
        "escrow_locked": lender.escrow_locked or 0,
        "total_invested": lender.total_invested or 0,
        "total_returns": lender.total_returns or 0,
        "total_withdrawn": getattr(lender, 'total_withdrawn', 0) or 0,
        "withdrawable": lender.wallet_balance or 0,
        "settled_investments": len(settled),
    }


# ═══════════════════════════════════════════════
#  REPAYMENT ENFORCEMENT ENGINE
# ═══════════════════════════════════════════════

OVERDUE_GRACE_DAYS = 7       # Days after due_date before marking 'overdue'
DEFAULT_THRESHOLD_DAYS = 30  # Days overdue before auto-default
LISTING_EXPIRY_DAYS = 60     # Days an unfunded listing stays open

@router.post("/enforce-repayments")
def enforce_repayments(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Repayment enforcement engine — call periodically (or via cron/admin trigger).
    1. Marks pending installments past due_date + grace as 'overdue'
    2. Auto-defaults listings where installments are overdue > threshold
    3. Expires stale open/partially_funded listings
    4. Releases escrow to lenders on settlement
    5. Triggers credit score recalculation for affected vendors
    """
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="Only admins can trigger repayment enforcement")

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    today_dt = datetime.now(timezone.utc)
    results = {"overdue_marked": 0, "defaults_triggered": 0, "listings_expired": 0, "escrow_released": 0, "scores_recalculated": []}

    # ── 1. Mark overdue installments ──
    pending_schedules = db.query(RepaymentSchedule).filter(
        RepaymentSchedule.status == "pending",
    ).all()

    vendors_to_rescore = set()
    for sched in pending_schedules:
        try:
            due_dt = datetime.strptime(sched.due_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue
        grace_deadline = due_dt + timedelta(days=OVERDUE_GRACE_DAYS)
        if today_dt >= grace_deadline:
            sched.status = "overdue"
            results["overdue_marked"] += 1

            # Notify vendor
            listing = db.query(MarketplaceListing).filter(MarketplaceListing.id == sched.listing_id).first()
            if listing:
                vendors_to_rescore.add(listing.vendor_id)
                vendor_user = db.query(User).filter(User.vendor_id == listing.vendor_id).first()
                if vendor_user:
                    db.add(Notification(
                        user_id=vendor_user.id,
                        title="Overdue Installment ⚠️",
                        message=f"Installment #{sched.installment_number} (₹{sched.total_amount:,.0f}) is overdue since {sched.due_date}. Please pay immediately to avoid default.",
                        notification_type="repayment",
                        link=f"/vendor/{listing.vendor_id}/invoices",
                    ))

    # ── 2. Auto-default listings with severely overdue installments ──
    funded_listings = db.query(MarketplaceListing).filter(
        MarketplaceListing.listing_status == "funded",
    ).all()

    for listing in funded_listings:
        overdue_schedules = db.query(RepaymentSchedule).filter(
            RepaymentSchedule.listing_id == listing.id,
            RepaymentSchedule.status == "overdue",
        ).all()

        if not overdue_schedules:
            continue

        # Check if any installment is past the default threshold
        worst_overdue_days = 0
        for sched in overdue_schedules:
            try:
                due_dt = datetime.strptime(sched.due_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                days_overdue = (today_dt - due_dt).days
                worst_overdue_days = max(worst_overdue_days, days_overdue)
            except (ValueError, TypeError):
                continue

        if worst_overdue_days >= DEFAULT_THRESHOLD_DAYS:
            listing.listing_status = "defaulted"
            results["defaults_triggered"] += 1
            vendors_to_rescore.add(listing.vendor_id)

            # Log on blockchain
            add_block(db, "default", {
                "type": "auto_default",
                "listing_id": listing.id,
                "days_overdue": worst_overdue_days,
                "overdue_installments": len(overdue_schedules),
                "defaulted_at": today_dt.isoformat(),
            })

            # Notify vendor
            vendor_user = db.query(User).filter(User.vendor_id == listing.vendor_id).first()
            if vendor_user:
                db.add(Notification(
                    user_id=vendor_user.id,
                    title="Listing Defaulted ❌",
                    message=f"Your listing has been marked as DEFAULTED due to {len(overdue_schedules)} overdue installments ({worst_overdue_days} days overdue). This will severely impact your credit score.",
                    notification_type="default",
                    link=f"/vendor/{listing.vendor_id}/invoices",
                ))

            # Notify all investors
            investors = db.query(FractionalInvestment).filter(
                FractionalInvestment.listing_id == listing.id,
                FractionalInvestment.status == "active",
            ).all()
            for inv in investors:
                lender_user = db.query(User).filter(User.lender_id == inv.lender_id).first()
                if lender_user:
                    db.add(Notification(
                        user_id=lender_user.id,
                        title="Investment Default Alert 🚨",
                        message=f"A listing you invested ₹{inv.invested_amount:,.0f} in has defaulted ({worst_overdue_days} days overdue).",
                        notification_type="default",
                        link=f"/marketplace/{listing.id}",
                    ))

    # ── 3. Expire stale unfunded listings ──
    stale_listings = db.query(MarketplaceListing).filter(
        MarketplaceListing.listing_status.in_(["open", "partially_funded"]),
    ).all()

    for listing in stale_listings:
        if listing.created_at:
            created_dt = listing.created_at if listing.created_at.tzinfo else listing.created_at.replace(tzinfo=timezone.utc)
            days_open = (today_dt - created_dt).days
            if days_open >= LISTING_EXPIRY_DAYS:
                # Refund any partial investments before expiring
                partial_investments = db.query(FractionalInvestment).filter(
                    FractionalInvestment.listing_id == listing.id,
                    FractionalInvestment.status == "active",
                ).all()
                for inv in partial_investments:
                    inv_lender = db.query(Lender).filter(Lender.id == inv.lender_id).first()
                    if inv_lender:
                        inv_lender.wallet_balance = round((inv_lender.wallet_balance or 0) + inv.invested_amount, 2)
                        inv_lender.escrow_locked = round(max(0, (inv_lender.escrow_locked or 0) - inv.invested_amount), 2)
                        results["escrow_released"] += 1
                    inv.status = "refunded"

                listing.listing_status = "expired"
                results["listings_expired"] += 1

                # Reset invoice listing flag
                invoice = db.query(Invoice).filter(Invoice.id == listing.invoice_id).first()
                if invoice:
                    invoice.is_listed = False

                vendor_user = db.query(User).filter(User.vendor_id == listing.vendor_id).first()
                if vendor_user:
                    db.add(Notification(
                        user_id=vendor_user.id,
                        title="Listing Expired ⏰",
                        message=f"Your listing has expired after {days_open} days without full funding. You may re-list the invoice.",
                        notification_type="listing",
                        link=f"/vendor/{listing.vendor_id}/invoices",
                    ))

    # ── 4. Release escrow for settled listings ──
    settled_listings = db.query(MarketplaceListing).filter(
        MarketplaceListing.listing_status == "settled",
    ).all()

    for listing in settled_listings:
        # Check if escrow has already been released (no active investments with locked escrow)
        active_investments = db.query(FractionalInvestment).filter(
            FractionalInvestment.listing_id == listing.id,
            FractionalInvestment.status == "active",
        ).all()

        for inv in active_investments:
            inv_lender = db.query(Lender).filter(Lender.id == inv.lender_id).first()
            if inv_lender:
                # Release escrow + add returns
                release_amount = inv.invested_amount
                return_amount = inv.expected_return or 0
                inv_lender.escrow_locked = round(max(0, (inv_lender.escrow_locked or 0) - release_amount), 2)
                inv_lender.wallet_balance = round((inv_lender.wallet_balance or 0) + release_amount + return_amount, 2)
                inv_lender.total_returns = round((inv_lender.total_returns or 0) + return_amount, 2)
                results["escrow_released"] += 1
            inv.status = "settled"

    # ── 5. Trigger credit score recalculation for affected vendors ──
    for vendor_id in vendors_to_rescore:
        try:
            from services.credit_scoring import compute_credit_score
            compute_credit_score(db, vendor_id)
            results["scores_recalculated"].append(vendor_id)
        except Exception:
            pass  # Don't fail the whole enforcement if one score fails

    db.commit()

    return {
        "message": "Repayment enforcement completed",
        "overdue_marked": results["overdue_marked"],
        "defaults_triggered": results["defaults_triggered"],
        "listings_expired": results["listings_expired"],
        "escrow_released": results["escrow_released"],
        "vendors_rescored": results["scores_recalculated"],
        "enforcement_date": today,
    }

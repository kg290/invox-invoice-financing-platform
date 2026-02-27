"""
Seed route — populates the database with realistic Indian demo data.
Vendors, invoices, marketplace listings, lenders, and verification checks.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import Vendor, Invoice, InvoiceItem, Lender, MarketplaceListing, VerificationCheck, User
from blockchain import add_block
from datetime import datetime, timezone
import bcrypt

router = APIRouter(prefix="/api/seed", tags=["Seed / Demo"])


def _hash_password(password: str) -> str:
    """Hash password using bcrypt directly (avoids passlib compatibility issues)."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

# Demo credentials — known passwords for quick login
DEMO_PASSWORD = "Demo@1234"

DEMO_USERS = [
    {"name": "Sunita Devi Verma", "email": "vendor1@invox.demo", "phone": "9876543210", "role": "vendor", "vendor_idx": 0},
    {"name": "Ramu Vishwakarma", "email": "vendor2@invox.demo", "phone": "9123456780", "role": "vendor", "vendor_idx": 1},
    {"name": "Fatima Bee Khan", "email": "vendor3@invox.demo", "phone": "9090909090", "role": "vendor", "vendor_idx": 2},
    {"name": "Deepak Jain", "email": "lender@invox.demo", "phone": "9811111111", "role": "lender", "lender_idx": 0},
]

DEMO_VENDORS = [
    # ── 1. Tiffin / Cloud Kitchen Service ──
    {
        "full_name": "Sunita Devi Verma",
        "date_of_birth": "1986-04-12",
        "phone": "9876543210",
        "email": "sunita.tiffin@gmail.com",
        "personal_pan": "BVDPS4321K",
        "personal_aadhaar": "234567891234",
        "address": "H-12, Laxmi Nagar, Near Metro Pillar 42",
        "city": "New Delhi",
        "state": "Delhi",
        "pincode": "110092",
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
        "gstin": "07BVDPS4321K1Z3",
        "gst_registration_date": "2020-01-15",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 24,
        "gst_compliance_status": "Regular",
        "cibil_score": 672,
        "annual_turnover": 480000,
        "monthly_revenue": 40000,
        "business_assets_value": 85000,
        "existing_liabilities": 25000,
        "bank_account_number": "10234567890",
        "bank_name": "State Bank of India",
        "bank_ifsc": "SBIN0009876",
        "bank_branch": "Laxmi Nagar",
        "nominee_name": "Rajan Verma",
        "nominee_relationship": "Husband",
        "nominee_phone": "9876543211",
        "nominee_aadhaar": "345678912345",
        "profile_status": "verified",
        "risk_score": 45,
    },
    # ── 2. Small Furniture Workshop ──
    {
        "full_name": "Ramu Vishwakarma",
        "date_of_birth": "1979-09-08",
        "phone": "9123456780",
        "email": "ramu.furniture@gmail.com",
        "personal_pan": "CVRPV5678L",
        "personal_aadhaar": "456789012345",
        "address": "Gali No. 3, Kirti Nagar, Industrial Area",
        "city": "New Delhi",
        "state": "Delhi",
        "pincode": "110015",
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
        "gstin": "07CVRPV5678L1Z6",
        "gst_registration_date": "2018-06-01",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 30,
        "gst_compliance_status": "Regular",
        "cibil_score": 698,
        "annual_turnover": 720000,
        "monthly_revenue": 60000,
        "business_assets_value": 180000,
        "existing_liabilities": 65000,
        "bank_account_number": "20345678901",
        "bank_name": "Punjab National Bank",
        "bank_ifsc": "PUNB0123400",
        "bank_branch": "Kirti Nagar",
        "nominee_name": "Geeta Devi",
        "nominee_relationship": "Wife",
        "nominee_phone": "9123456781",
        "nominee_aadhaar": "567890123456",
        "profile_status": "verified",
        "risk_score": 38,
    },
    # ── 3. Small Spice & Dhaba Supplier ──
    {
        "full_name": "Fatima Bee Khan",
        "date_of_birth": "1988-03-14",
        "phone": "9090909090",
        "email": "fatima.spices@gmail.com",
        "personal_pan": "FKBPK7890P",
        "personal_aadhaar": "012345678901",
        "address": "Sarafa Bazaar, Old Bhopal",
        "city": "Bhopal",
        "state": "Madhya Pradesh",
        "pincode": "462001",
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
        "gstin": "23FKBPK7890P1Z7",
        "gst_registration_date": "2019-01-01",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 24,
        "gst_compliance_status": "Regular",
        "cibil_score": 660,
        "annual_turnover": 600000,
        "monthly_revenue": 50000,
        "business_assets_value": 140000,
        "existing_liabilities": 35000,
        "bank_account_number": "50678901234",
        "bank_name": "Central Bank of India",
        "bank_ifsc": "CBIN0281234",
        "bank_branch": "New Market, Bhopal",
        "nominee_name": "Salim Khan",
        "nominee_relationship": "Husband",
        "nominee_phone": "9090909091",
        "nominee_aadhaar": "123456789012",
        "profile_status": "verified",
        "risk_score": 40,
    },
]

DEMO_LENDERS = [
    {"name": "Deepak Jain", "email": "deepak.jain@microfinance.in", "phone": "9811111111", "organization": "JanSeva Microfinance", "lender_type": "nbfc"},
    {"name": "Meena Patel", "email": "meena.patel@gmail.com", "phone": "9822222222", "organization": None, "lender_type": "individual"},
    {"name": "Harish Bansal", "email": "harish@sahayakfund.in", "phone": "9833333333", "organization": "Sahayak Small Biz Fund", "lender_type": "nbfc"},
]

DEMO_INVOICES = [
    # ── Vendor 0: Tiffin Service — monthly catering to a small IT office ──
    (0, {
        "invoice_number": "INV-2026-001",
        "invoice_date": "2026-01-15",
        "due_date": "2026-02-15",
        "supply_type": "intra_state",
        "place_of_supply": "Delhi",
        "place_of_supply_code": "07",
        "reverse_charge": False,
        "buyer_name": "BrightStar Co-Working Space",
        "buyer_gstin": "07AABCB9876K1Z4",
        "buyer_address": "2nd Floor, Preet Vihar",
        "buyer_city": "New Delhi",
        "buyer_state": "Delhi",
        "buyer_state_code": "07",
        "buyer_pincode": "110092",
        "buyer_phone": "9999888877",
        "buyer_email": "admin@brightstar.co.in",
        "notes": "Monthly tiffin supply for 30 employees — Jan 2026",
        "terms": "Payment within 15 days of invoice",
        "invoice_status": "issued",
        "items": [
            {"description": "Veg Lunch Tiffin (30 days x 25 pax)", "hsn_sac_code": "996331", "quantity": 750, "unit": "NOS", "unit_price": 18, "gst_rate": 5},
            {"description": "Evening Snack Box (30 days x 25 pax)", "hsn_sac_code": "996331", "quantity": 750, "unit": "NOS", "unit_price": 8, "gst_rate": 5},
            {"description": "Disposable Packaging & Delivery", "hsn_sac_code": "392410", "quantity": 1, "unit": "LOT", "unit_price": 1200, "gst_rate": 18},
        ],
    }),
    # ── Vendor 1: Furniture — school benches order ──
    (1, {
        "invoice_number": "INV-2026-002",
        "invoice_date": "2026-01-20",
        "due_date": "2026-03-20",
        "supply_type": "intra_state",
        "place_of_supply": "Delhi",
        "place_of_supply_code": "07",
        "reverse_charge": False,
        "buyer_name": "Saraswati Vidya Mandir School",
        "buyer_gstin": "07AACTS1234M1Z8",
        "buyer_address": "Rajouri Garden, Ring Road",
        "buyer_city": "New Delhi",
        "buyer_state": "Delhi",
        "buyer_state_code": "07",
        "buyer_pincode": "110027",
        "buyer_phone": "9876512345",
        "buyer_email": "office@saraswatischool.in",
        "notes": "Classroom furniture for new wing — wooden benches & teacher desks",
        "terms": "50% advance paid, 50% on delivery. Net 30.",
        "invoice_status": "issued",
        "items": [
            {"description": "Wooden Dual-Seater Bench with Desk", "hsn_sac_code": "94016100", "quantity": 15, "unit": "PCS", "unit_price": 1800, "gst_rate": 18},
            {"description": "Teacher Table (Teak, 4x2.5 ft)", "hsn_sac_code": "94016100", "quantity": 3, "unit": "PCS", "unit_price": 3200, "gst_rate": 18},
            {"description": "Wooden Almirah (Small)", "hsn_sac_code": "94016100", "quantity": 2, "unit": "PCS", "unit_price": 4500, "gst_rate": 18},
        ],
    }),
    # ── Vendor 2: Spice Trader — monthly masala supply to a dhaba chain ──
    (2, {
        "invoice_number": "INV-2026-005",
        "invoice_date": "2026-02-10",
        "due_date": "2026-03-10",
        "supply_type": "intra_state",
        "place_of_supply": "Madhya Pradesh",
        "place_of_supply_code": "23",
        "reverse_charge": False,
        "buyer_name": "Highway Dhaba — Raju Bhai",
        "buyer_gstin": "23AABCH9012E1Z5",
        "buyer_address": "NH-12, Raisen Road",
        "buyer_city": "Bhopal",
        "buyer_state": "Madhya Pradesh",
        "buyer_state_code": "23",
        "buyer_pincode": "462010",
        "buyer_phone": "9826543210",
        "buyer_email": "rajudhaba@gmail.com",
        "notes": "Monthly masala & spice supply — Feb 2026",
        "terms": "Payment within 15 days of delivery",
        "invoice_status": "issued",
        "items": [
            {"description": "Red Chilli Powder (Kashmiri)", "hsn_sac_code": "09042110", "quantity": 10, "unit": "KGS", "unit_price": 320, "gst_rate": 5},
            {"description": "Turmeric Powder (Salem)", "hsn_sac_code": "09103010", "quantity": 8, "unit": "KGS", "unit_price": 180, "gst_rate": 5},
            {"description": "Garam Masala (House Blend)", "hsn_sac_code": "09109100", "quantity": 5, "unit": "KGS", "unit_price": 450, "gst_rate": 5},
            {"description": "Coriander Powder", "hsn_sac_code": "09092110", "quantity": 6, "unit": "KGS", "unit_price": 160, "gst_rate": 5},
            {"description": "Cumin Whole (Rajasthani)", "hsn_sac_code": "09093110", "quantity": 4, "unit": "KGS", "unit_price": 520, "gst_rate": 5},
        ],
    }),
]


def _calc_item(item_data: dict, supply_type: str):
    """Calculate tax amounts for a single item."""
    qty = item_data["quantity"]
    price = item_data["unit_price"]
    taxable = qty * price
    gst_rate = item_data["gst_rate"]
    gst_amt = round(taxable * gst_rate / 100, 2)
    if supply_type == "intra_state":
        return {**item_data, "taxable_value": taxable, "cgst_amount": round(gst_amt / 2, 2), "sgst_amount": round(gst_amt / 2, 2), "igst_amount": 0, "cess_rate": 0, "cess_amount": 0, "discount_percent": 0, "discount_amount": 0, "total_amount": round(taxable + gst_amt, 2)}
    else:
        return {**item_data, "taxable_value": taxable, "cgst_amount": 0, "sgst_amount": 0, "igst_amount": gst_amt, "cess_rate": 0, "cess_amount": 0, "discount_percent": 0, "discount_amount": 0, "total_amount": round(taxable + gst_amt, 2)}


@router.post("/demo")
def seed_demo_data(db: Session = Depends(get_db)):
    """Seed database with 3 small-scale Indian vendor profiles, 3 invoices, 3 lenders, verification checks & marketplace listings."""

    # Check if already seeded
    if db.query(Vendor).count() > 0:
        return {"message": "Demo data already exists", "seeded": False}

    created = {"vendors": 0, "invoices": 0, "lenders": 0, "listings": 0, "checks": 0}

    # ── 1. Vendors ──
    vendors = []
    for v_data in DEMO_VENDORS:
        vendor = Vendor(**v_data)
        db.add(vendor)
        db.flush()
        vendors.append(vendor)
        created["vendors"] += 1

        # Verification checks
        for check_type in ["gstin", "pan", "aadhaar", "cibil", "bank", "pan_gstin_match", "address"]:
            vc = VerificationCheck(
                vendor_id=vendor.id,
                check_type=check_type,
                status="passed",
                details=f'{{"result": "valid", "source": "demo_seed"}}',
            )
            db.add(vc)
            created["checks"] += 1

    # ── 2. Lenders ──
    lenders = []
    for l_data in DEMO_LENDERS:
        lender = Lender(**l_data)
        db.add(lender)
        db.flush()
        lenders.append(lender)
        created["lenders"] += 1

    # ── 3. Invoices + Marketplace Listings ──
    for vendor_idx, inv_data in DEMO_INVOICES:
        vendor = vendors[vendor_idx]
        items_raw = inv_data.pop("items")
        supply_type = inv_data["supply_type"]

        # Calculate totals
        processed_items = [_calc_item(it, supply_type) for it in items_raw]
        subtotal = sum(it["taxable_value"] for it in processed_items)
        total_cgst = sum(it["cgst_amount"] for it in processed_items)
        total_sgst = sum(it["sgst_amount"] for it in processed_items)
        total_igst = sum(it["igst_amount"] for it in processed_items)
        grand_total = round(subtotal + total_cgst + total_sgst + total_igst, 2)

        invoice = Invoice(
            vendor_id=vendor.id,
            **inv_data,
            subtotal=subtotal,
            total_cgst=total_cgst,
            total_sgst=total_sgst,
            total_igst=total_igst,
            total_cess=0,
            total_discount=0,
            round_off=0,
            grand_total=grand_total,
            is_listed=True,
            listed_at=datetime.now(timezone.utc),
        )
        db.add(invoice)
        db.flush()

        # Items
        for idx, it in enumerate(processed_items, 1):
            item = InvoiceItem(invoice_id=invoice.id, item_number=idx, **it)
            db.add(item)

        # Blockchain
        block_hash = None
        try:
            block = add_block(db, "invoice", {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "vendor_id": vendor.id,
                "grand_total": grand_total,
            })
            block_hash = block.block_hash
            invoice.blockchain_hash = block_hash
            invoice.block_index = block.block_index
        except Exception:
            pass

        # Marketplace listing
        requested_pct = 80
        requested_amt = round(grand_total * requested_pct / 100, 2)
        listing = MarketplaceListing(
            invoice_id=invoice.id,
            vendor_id=vendor.id,
            requested_percentage=requested_pct,
            requested_amount=requested_amt,
            discount_rate=round(12 + vendor_idx * 0.5, 1),
            max_interest_rate=round(14 + vendor_idx, 1),
            repayment_period_days=90,
            listing_status="open",
            risk_score=vendor.risk_score,
            blockchain_hash=block_hash,
        )
        db.add(listing)
        created["invoices"] += 1
        created["listings"] += 1

    db.commit()

    # ── 4. Demo User Accounts ──
    users_created = 0
    for u_data in DEMO_USERS:
        # Skip if user already exists
        if db.query(User).filter(User.email == u_data["email"]).first():
            continue
        user = User(
            name=u_data["name"],
            email=u_data["email"],
            phone=u_data["phone"],
            password_hash=_hash_password(DEMO_PASSWORD),
            role=u_data["role"],
            is_verified=True,
            is_active=True,
            vendor_id=vendors[u_data["vendor_idx"]].id if u_data.get("vendor_idx") is not None else None,
            lender_id=lenders[u_data["lender_idx"]].id if u_data.get("lender_idx") is not None else None,
        )
        db.add(user)
        users_created += 1
    db.commit()

    vendor_ids = [v.id for v in vendors]
    lender_ids = [l.id for l in lenders]

    return {
        "message": "Demo data seeded successfully!",
        "seeded": True,
        "created": created,
        "vendor_ids": vendor_ids,
        "lender_ids": lender_ids,
        "demo_logins": [
            {"role": "Vendor 1 (Tiffin)", "email": "vendor1@invox.demo", "password": DEMO_PASSWORD},
            {"role": "Vendor 2 (Furniture)", "email": "vendor2@invox.demo", "password": DEMO_PASSWORD},
            {"role": "Vendor 3 (Spices)", "email": "vendor3@invox.demo", "password": DEMO_PASSWORD},
            {"role": "Lender", "email": "lender@invox.demo", "password": DEMO_PASSWORD},
        ],
    }


@router.post("/demo-users")
def seed_demo_users(db: Session = Depends(get_db)):
    """Create demo login accounts linked to existing vendors/lenders. Safe to call multiple times."""
    vendors = db.query(Vendor).order_by(Vendor.id).all()
    lenders = db.query(Lender).order_by(Lender.id).all()

    if not vendors:
        return {"message": "No vendors found — run /api/seed/demo first", "created": 0}

    created = 0
    accounts = []
    for u_data in DEMO_USERS:
        existing = db.query(User).filter(User.email == u_data["email"]).first()
        if existing:
            accounts.append({"email": u_data["email"], "status": "already exists", "role": u_data["role"]})
            continue

        vendor_id = None
        lender_id = None
        if u_data.get("vendor_idx") is not None and u_data["vendor_idx"] < len(vendors):
            vendor_id = vendors[u_data["vendor_idx"]].id
        if u_data.get("lender_idx") is not None and u_data["lender_idx"] < len(lenders):
            lender_id = lenders[u_data["lender_idx"]].id

        user = User(
            name=u_data["name"],
            email=u_data["email"],
            phone=u_data["phone"],
            password_hash=_hash_password(DEMO_PASSWORD),
            role=u_data["role"],
            is_verified=True,
            is_active=True,
            vendor_id=vendor_id,
            lender_id=lender_id,
        )
        db.add(user)
        created += 1
        accounts.append({"email": u_data["email"], "status": "created", "role": u_data["role"]})

    db.commit()
    return {
        "message": f"Created {created} demo user accounts",
        "created": created,
        "accounts": accounts,
        "demo_logins": [
            {"role": "Vendor 1 (Tiffin)", "email": "vendor1@invox.demo", "password": DEMO_PASSWORD},
            {"role": "Vendor 2 (Furniture)", "email": "vendor2@invox.demo", "password": DEMO_PASSWORD},
            {"role": "Vendor 3 (Spices)", "email": "vendor3@invox.demo", "password": DEMO_PASSWORD},
            {"role": "Lender", "email": "lender@invox.demo", "password": DEMO_PASSWORD},
        ],
    }

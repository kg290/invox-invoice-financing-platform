from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text, Boolean, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


# ════════════════════════════════════════════════
#  USER / AUTH
# ════════════════════════════════════════════════
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(200), nullable=False)
    email = Column(String(200), unique=True, nullable=False, index=True)
    phone = Column(String(15), nullable=True)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False)  # vendor, lender, admin
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    lender_id = Column(Integer, ForeignKey("lenders.id"), nullable=True)
    otp_code = Column(String(6), nullable=True)
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)
    otp_channel = Column(String(20), nullable=True)  # whatsapp, sms, email
    is_verified = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    notifications = relationship("Notification", back_populates="user")


# ════════════════════════════════════════════════
#  NOTIFICATION
# ════════════════════════════════════════════════
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    notification_type = Column(String(50), nullable=False)  # funding, verification, settlement, system, otp
    is_read = Column(Boolean, default=False)
    link = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")


# ════════════════════════════════════════════════
#  REPAYMENT SCHEDULE
# ════════════════════════════════════════════════
class RepaymentSchedule(Base):
    __tablename__ = "repayment_schedules"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"), nullable=False)
    installment_number = Column(Integer, nullable=False)
    due_date = Column(String(10), nullable=False)  # YYYY-MM-DD
    principal_amount = Column(Float, nullable=False)
    interest_amount = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    status = Column(String(20), default="pending")  # pending, paid, overdue
    paid_date = Column(String(10), nullable=True)
    paid_amount = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ════════════════════════════════════════════════
#  ACTIVITY LOG
# ════════════════════════════════════════════════
class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    entity_type = Column(String(50), nullable=False)  # vendor, invoice, listing, lender, user
    entity_id = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    user_id = Column(Integer, nullable=True)
    metadata_json = Column(Text, nullable=True)  # JSON string
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # ── Personal Details ──
    full_name = Column(String(255), nullable=False)
    date_of_birth = Column(String(10), nullable=False)  # YYYY-MM-DD
    phone = Column(String(15), nullable=False, unique=True)
    email = Column(String(255), nullable=False, unique=True)
    personal_pan = Column(String(10), nullable=False, unique=True)
    personal_aadhaar = Column(String(12), nullable=False, unique=True)
    address = Column(Text, nullable=False)
    city = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    pincode = Column(String(6), nullable=False)

    # ── Business Details ──
    business_name = Column(String(255), nullable=False)
    business_type = Column(String(50), nullable=False)  # Proprietorship, Partnership, LLP, Pvt Ltd, etc.
    business_category = Column(String(100), nullable=False)  # Manufacturing, Trading, Services, etc.
    business_registration_number = Column(String(50), nullable=True)
    udyam_registration_number = Column(String(30), nullable=True)  # MSME registration
    year_of_establishment = Column(Integer, nullable=False)
    number_of_employees = Column(Integer, nullable=True)
    business_address = Column(Text, nullable=False)
    business_city = Column(String(100), nullable=False)
    business_state = Column(String(100), nullable=False)
    business_pincode = Column(String(6), nullable=False)

    # ── GST Details ──
    gstin = Column(String(15), nullable=False, unique=True)
    gst_registration_date = Column(String(10), nullable=False)
    gst_filing_frequency = Column(String(20), nullable=False)  # Monthly, Quarterly
    total_gst_filings = Column(Integer, nullable=False, default=0)
    gst_compliance_status = Column(String(20), nullable=False, default="Regular")  # Regular, Irregular, Defaulter

    # ── Financial Details ──
    cibil_score = Column(Integer, nullable=False)
    annual_turnover = Column(Float, nullable=False)
    monthly_revenue = Column(Float, nullable=True)
    business_assets_value = Column(Float, nullable=False, default=0)
    existing_liabilities = Column(Float, nullable=True, default=0)
    bank_account_number = Column(String(20), nullable=False)
    bank_name = Column(String(100), nullable=False)
    bank_ifsc = Column(String(11), nullable=False)
    bank_branch = Column(String(100), nullable=True)

    # ── Business Profile (marketplace-facing) ──
    business_description = Column(Text, nullable=True)  # What the business does
    business_images = Column(Text, nullable=True)  # JSON array of image paths
    total_reviews = Column(Integer, nullable=True, default=0)
    average_rating = Column(Float, nullable=True, default=0.0)

    # ── Document Uploads (store file paths) ──
    business_pan_doc = Column(String(500), nullable=True)
    business_aadhaar_doc = Column(String(500), nullable=True)
    electricity_bill_doc = Column(String(500), nullable=True)
    bank_statement_doc = Column(String(500), nullable=True)
    registration_certificate_doc = Column(String(500), nullable=True)
    gst_certificate_doc = Column(String(500), nullable=True)

    # ── Nominee Details ──
    nominee_name = Column(String(255), nullable=False)
    nominee_relationship = Column(String(50), nullable=False)
    nominee_phone = Column(String(15), nullable=False)
    nominee_aadhaar = Column(String(12), nullable=True)

    # ── System Fields ──
    profile_status = Column(String(20), nullable=False, default="pending")  # pending, verified, rejected
    verification_notes = Column(Text, nullable=True)
    risk_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    invoices = relationship("Invoice", back_populates="vendor")
    verification_checks = relationship("VerificationCheck", back_populates="vendor")


# ════════════════════════════════════════════════
#  VERIFICATION CHECKS
# ════════════════════════════════════════════════
class VerificationCheck(Base):
    __tablename__ = "verification_checks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    check_type = Column(String(50), nullable=False)  # gstin, pan, aadhaar, cibil, bank, pan_gstin_match, address
    status = Column(String(20), nullable=False, default="pending")  # pending, passed, failed, warning
    details = Column(Text, nullable=True)  # JSON string of check results
    checked_at = Column(DateTime(timezone=True), server_default=func.now())

    vendor = relationship("Vendor", back_populates="verification_checks")


# ════════════════════════════════════════════════
#  INVOICE & LINE ITEMS (GST-compliant)
# ════════════════════════════════════════════════
class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    invoice_number = Column(String(50), nullable=False, unique=True)
    invoice_date = Column(String(10), nullable=False)
    due_date = Column(String(10), nullable=False)

    # ── Supply Details ──
    supply_type = Column(String(20), nullable=False)  # intra_state, inter_state
    place_of_supply = Column(String(100), nullable=False)  # State name
    place_of_supply_code = Column(String(2), nullable=False)  # 2-digit state code
    reverse_charge = Column(Boolean, nullable=False, default=False)

    # ── Buyer Details ──
    buyer_name = Column(String(255), nullable=False)
    buyer_gstin = Column(String(15), nullable=True)  # Optional for B2C
    buyer_address = Column(Text, nullable=False)
    buyer_city = Column(String(100), nullable=False)
    buyer_state = Column(String(100), nullable=False)
    buyer_state_code = Column(String(2), nullable=False)
    buyer_pincode = Column(String(6), nullable=False)
    buyer_phone = Column(String(15), nullable=True)
    buyer_email = Column(String(255), nullable=True)

    # ── Totals (auto-calculated) ──
    subtotal = Column(Float, nullable=False, default=0)
    total_cgst = Column(Float, nullable=False, default=0)
    total_sgst = Column(Float, nullable=False, default=0)
    total_igst = Column(Float, nullable=False, default=0)
    total_cess = Column(Float, nullable=False, default=0)
    total_discount = Column(Float, nullable=False, default=0)
    round_off = Column(Float, nullable=False, default=0)
    grand_total = Column(Float, nullable=False, default=0)

    # ── Additional ──
    notes = Column(Text, nullable=True)
    terms = Column(Text, nullable=True)
    invoice_status = Column(String(20), nullable=False, default="draft")  # draft, issued, paid, overdue, cancelled
    payment_status = Column(String(20), nullable=False, default="unpaid")  # unpaid, partial, paid

    # ── Blockchain ──
    blockchain_hash = Column(String(64), nullable=True)
    block_index = Column(Integer, nullable=True)

    # ── Marketplace ──
    is_listed = Column(Boolean, nullable=False, default=False)
    listed_at = Column(DateTime(timezone=True), nullable=True)

    # ── System ──
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    vendor = relationship("Vendor", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
    marketplace_listing = relationship("MarketplaceListing", back_populates="invoice", uselist=False)


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    item_number = Column(Integer, nullable=False)  # Serial no within invoice

    description = Column(String(500), nullable=False)
    hsn_sac_code = Column(String(8), nullable=False)  # HSN for goods, SAC for services
    quantity = Column(Float, nullable=False)
    unit = Column(String(20), nullable=False)  # NOS, KGS, LTR, MTR, SQM, PCS, BOX, etc.
    unit_price = Column(Float, nullable=False)
    discount_percent = Column(Float, nullable=False, default=0)
    discount_amount = Column(Float, nullable=False, default=0)

    taxable_value = Column(Float, nullable=False)  # (qty * unit_price) - discount
    gst_rate = Column(Float, nullable=False)  # 0, 5, 12, 18, 28
    cgst_amount = Column(Float, nullable=False, default=0)
    sgst_amount = Column(Float, nullable=False, default=0)
    igst_amount = Column(Float, nullable=False, default=0)
    cess_rate = Column(Float, nullable=False, default=0)
    cess_amount = Column(Float, nullable=False, default=0)
    total_amount = Column(Float, nullable=False)

    invoice = relationship("Invoice", back_populates="items")


# ════════════════════════════════════════════════
#  MARKETPLACE
# ════════════════════════════════════════════════
class MarketplaceListing(Base):
    __tablename__ = "marketplace_listings"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, unique=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)

    listing_title = Column(String(255), nullable=True)  # Vendor-provided title for the listing
    listing_description = Column(Text, nullable=True)  # Vendor-provided description

    requested_percentage = Column(Float, nullable=False, default=80)  # 70-80%
    requested_amount = Column(Float, nullable=False)
    discount_rate = Column(Float, nullable=True)  # Annual interest/discount offered
    max_interest_rate = Column(Float, nullable=False, default=15)  # Max interest % vendor can afford
    repayment_period_days = Column(Integer, nullable=False, default=90)  # Days to return money

    listing_status = Column(String(20), nullable=False, default="open")  # open, funded, settled, cancelled, expired
    funded_amount = Column(Float, nullable=True)
    funded_by = Column(String(255), nullable=True)  # Lender name/id
    lender_id = Column(Integer, ForeignKey("lenders.id"), nullable=True)
    funded_at = Column(DateTime(timezone=True), nullable=True)
    settlement_date = Column(DateTime(timezone=True), nullable=True)

    risk_score = Column(Float, nullable=True)  # AI risk score at time of listing
    blockchain_hash = Column(String(64), nullable=True)
    pdf_hash = Column(String(64), nullable=True)  # Hash of encrypted invoice PDF

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    invoice = relationship("Invoice", back_populates="marketplace_listing")
    lender = relationship("Lender", back_populates="funded_listings")


# ════════════════════════════════════════════════
#  LENDER
# ════════════════════════════════════════════════
class Lender(Base):
    __tablename__ = "lenders"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    phone = Column(String(15), nullable=True)
    organization = Column(String(255), nullable=True)
    lender_type = Column(String(50), nullable=False, default="individual")  # individual, nbfc, bank
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    funded_listings = relationship("MarketplaceListing", back_populates="lender")


# ════════════════════════════════════════════════
#  BLOCKCHAIN LEDGER
# ════════════════════════════════════════════════
class BlockchainBlock(Base):
    __tablename__ = "blockchain_blocks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    block_index = Column(Integer, nullable=False, unique=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    data_type = Column(String(50), nullable=False)  # invoice, listing, settlement, funding, refund
    data_hash = Column(String(64), nullable=False)  # SHA-256 of the data
    data_summary = Column(Text, nullable=False)  # JSON summary (may be encrypted)
    previous_hash = Column(String(64), nullable=False)
    nonce = Column(Integer, nullable=False, default=0)
    block_hash = Column(String(64), nullable=False, unique=True)
    merkle_root = Column(String(64), nullable=True)  # Merkle tree root of data fields
    digital_signature = Column(String(128), nullable=True)  # HMAC-SHA256 signature
    is_encrypted = Column(Boolean, default=False)  # Whether data_summary is encrypted


# ════════════════════════════════════════════════
#  INVOX PAY PAYMENTS
# ════════════════════════════════════════════════
class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    gateway_order_id = Column(String(100), nullable=False, unique=True)
    gateway_payment_id = Column(String(100), nullable=True)
    gateway_signature = Column(String(256), nullable=True)

    amount = Column(Float, nullable=False)         # in INR
    currency = Column(String(10), default="INR")
    status = Column(String(30), default="created")  # created, paid, failed, refunded

    # What this payment is for
    payment_type = Column(String(30), nullable=False)  # funding, repayment
    payment_method = Column(String(30), nullable=True)  # card, upi, netbanking
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"), nullable=True)
    installment_id = Column(Integer, ForeignKey("repayment_schedules.id"), nullable=True)

    # Who is paying
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    payer_name = Column(String(255), nullable=True)
    payer_email = Column(String(255), nullable=True)

    notes_json = Column(Text, nullable=True)  # JSON string of additional context
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)


# ════════════════════════════════════════════════
#  BLOCKCHAIN INVOICE REGISTRY
# ════════════════════════════════════════════════
class InvoiceRegistryEntry(Base):
    __tablename__ = "invoice_registry"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, unique=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)

    # Cryptographic proof
    invoice_hash = Column(String(64), nullable=False, unique=True)      # SHA-256 of canonical invoice data
    vendor_signature = Column(String(128), nullable=False)               # HMAC-SHA256 vendor signature
    buyer_gstin_hash = Column(String(64), nullable=True)                # Hashed buyer GSTIN
    gstn_reference = Column(String(100), nullable=True)                 # Reference from GST portal

    # Blockchain anchoring
    block_index = Column(Integer, nullable=True)
    block_hash = Column(String(64), nullable=True)
    merkle_root = Column(String(64), nullable=True)

    # Registry metadata
    registration_status = Column(String(20), nullable=False, default="pending")  # pending, registered, rejected, tampered
    tamper_check_count = Column(Integer, default=0)
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    verification_result = Column(String(20), nullable=True)  # intact, tampered

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ════════════════════════════════════════════════
#  TRIPLE VERIFICATION — VERIFICATION REPORTS
# ════════════════════════════════════════════════
class InvoiceVerificationReport(Base):
    __tablename__ = "invoice_verification_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)

    # Layer 1: Document Verification
    layer1_status = Column(String(20), nullable=False, default="pending")  # passed, failed, warning
    layer1_score = Column(Float, default=0)          # 0-100
    layer1_details = Column(Text, nullable=True)     # JSON

    # Layer 2: Entity Verification
    layer2_status = Column(String(20), nullable=False, default="pending")
    layer2_score = Column(Float, default=0)
    layer2_details = Column(Text, nullable=True)

    # Layer 3: Behavioral Verification
    layer3_status = Column(String(20), nullable=False, default="pending")
    layer3_score = Column(Float, default=0)
    layer3_details = Column(Text, nullable=True)

    # Overall
    overall_status = Column(String(20), nullable=False, default="pending")  # verified, rejected, needs_review
    overall_score = Column(Float, default=0)                                # 0-100 composite
    risk_flags = Column(Text, nullable=True)                                # JSON array of flags
    recommendation = Column(String(50), nullable=True)                      # approve, reject, manual_review

    # WhiteBooks GST API response (raw)
    gst_api_response = Column(Text, nullable=True)

    verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ════════════════════════════════════════════════
#  CREDIT SCORING ENGINE
# ════════════════════════════════════════════════
class CreditScore(Base):
    __tablename__ = "credit_scores"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)

    # Composite score
    total_score = Column(Float, nullable=False)          # 0-100
    risk_grade = Column(String(5), nullable=False)       # AAA, AA, A, BBB, BB, B, C, D
    confidence_level = Column(Float, default=0)          # 0-1 how reliable

    # Component scores (all 0-100)
    cibil_component = Column(Float, default=0)
    gst_compliance_component = Column(Float, default=0)
    repayment_history_component = Column(Float, default=0)
    bank_health_component = Column(Float, default=0)
    invoice_quality_component = Column(Float, default=0)
    business_stability_component = Column(Float, default=0)

    # Derived recommendations
    recommended_interest_rate = Column(Float, nullable=True)   # %
    recommended_max_funding = Column(Float, nullable=True)     # ₹
    recommended_max_tenure_days = Column(Integer, nullable=True)

    # Data snapshot
    data_snapshot_json = Column(Text, nullable=True)   # JSON of all input data at scoring time

    scored_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)   # Score validity window


# ════════════════════════════════════════════════
#  INVOICE FACTORING — RECOURSE OPTIONS
# ════════════════════════════════════════════════
class FactoringAgreement(Base):
    __tablename__ = "factoring_agreements"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    listing_id = Column(Integer, ForeignKey("marketplace_listings.id"), nullable=False, unique=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    lender_id = Column(Integer, nullable=True)

    # Factoring Type
    factoring_type = Column(String(20), nullable=False)   # non_recourse, partial_recourse, full_recourse
    recourse_percentage = Column(Float, nullable=False)     # 0 (non), 30 (partial), 100 (full)

    # Pricing
    base_interest_rate = Column(Float, nullable=False)
    risk_premium_rate = Column(Float, default=0)
    insurance_rate = Column(Float, default=0)
    effective_interest_rate = Column(Float, nullable=False)

    # Credit scores at time of agreement
    vendor_credit_score = Column(Float, nullable=True)
    buyer_credit_score = Column(Float, nullable=True)

    # Financials
    invoice_amount = Column(Float, nullable=True)
    funded_amount = Column(Float, nullable=True)
    tenure_days = Column(Integer, nullable=True)
    repayment_due_date = Column(DateTime(timezone=True), nullable=True)

    # Guarantee details
    personal_guarantee = Column(Boolean, default=False)
    mandate_id = Column(Integer, ForeignKey("emandate_registrations.id"), nullable=True)

    # Status
    agreement_status = Column(String(20), default="active")  # active, defaulted, completed, cancelled
    default_triggered = Column(Boolean, default=False)
    default_amount = Column(Float, nullable=True)
    default_recovery_amount = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


# ════════════════════════════════════════════════
#  NPCI e-MANDATE
# ════════════════════════════════════════════════
class EMandateRegistration(Base):
    __tablename__ = "emandate_registrations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    mandate_reference = Column(String(50), nullable=False, unique=True)

    # Bank details
    bank_account_number = Column(String(20), nullable=False)
    bank_ifsc = Column(String(11), nullable=False)
    bank_name = Column(String(100), nullable=True)

    # Mandate parameters
    max_amount = Column(Float, nullable=False)
    frequency = Column(String(20), default="monthly")  # weekly, monthly, quarterly, as_presented
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Status
    mandate_status = Column(String(20), default="pending")  # pending, active, paused, revoked, expired
    npci_response_json = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EMandateExecution(Base):
    __tablename__ = "emandate_executions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    mandate_id = Column(Integer, ForeignKey("emandate_registrations.id"), nullable=False)
    installment_id = Column(Integer, ForeignKey("repayment_schedules.id"), nullable=True)

    # Execution details
    execution_reference = Column(String(50), nullable=False, unique=True)
    amount = Column(Float, nullable=False)

    # Status
    execution_status = Column(String(20), default="initiated")  # initiated, success, failed, retrying
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    bank_response_json = Column(Text, nullable=True)

    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

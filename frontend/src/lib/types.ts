export interface VendorFormData {
  // Personal Details
  full_name: string;
  date_of_birth: string;
  phone: string;
  email: string;
  personal_pan: string;
  personal_aadhaar: string;
  address: string;
  city: string;
  state: string;
  pincode: string;

  // Business Details
  business_name: string;
  business_type: string;
  business_category: string;
  business_registration_number?: string;
  udyam_registration_number?: string;
  year_of_establishment: number;
  number_of_employees?: number;
  business_address: string;
  business_city: string;
  business_state: string;
  business_pincode: string;

  // GST Details
  gstin: string;
  gst_registration_date?: string;  // Auto-filled from GST portal
  gst_filing_frequency?: string;   // Auto-filled from GST portal
  total_gst_filings?: number;      // Auto-filled from GST portal
  gst_compliance_status?: string;  // Auto-filled from GST portal

  // Financial Details
  cibil_score?: number;  // Auto-fetched from CIBIL via PAN
  annual_turnover: number;
  monthly_revenue?: number;
  business_assets_value: number;
  existing_liabilities?: number;
  bank_account_number: string;
  bank_name: string;
  bank_ifsc: string;
  bank_branch?: string;

  // Nominee Details
  nominee_name: string;
  nominee_relationship: string;
  nominee_phone: string;
  nominee_aadhaar?: string;
}

export interface VendorResponse {
  id: number;
  full_name: string;
  phone: string;
  email: string;
  business_name: string;
  gstin: string;
  cibil_score: number;
  annual_turnover: number;
  profile_status: string;
  business_type: string;
  business_category: string;
  year_of_establishment: number;
  gst_compliance_status: string;
  business_assets_value: number;
  nominee_name: string;
}

export interface VendorDetailResponse extends VendorFormData {
  id: number;
  profile_status: string;
  risk_score: number | null;
  business_pan_doc: string | null;
  business_aadhaar_doc: string | null;
  electricity_bill_doc: string | null;
  bank_statement_doc: string | null;
  registration_certificate_doc: string | null;
  gst_certificate_doc: string | null;
}

export const INDIAN_STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
  "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
  "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
  "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
  "Uttar Pradesh", "Uttarakhand", "West Bengal",
  "Andaman and Nicobar Islands", "Chandigarh", "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi", "Jammu and Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
];

export const BUSINESS_TYPES = [
  "Proprietorship",
  "Partnership",
  "LLP (Limited Liability Partnership)",
  "Private Limited",
  "Public Limited",
  "One Person Company",
  "Hindu Undivided Family (HUF)",
];

export const BUSINESS_CATEGORIES = [
  "Manufacturing",
  "Trading",
  "Services",
  "Agriculture & Allied",
  "Construction",
  "Textiles",
  "Food Processing",
  "IT & Software",
  "Healthcare",
  "Education",
  "Transport & Logistics",
  "Retail",
  "Wholesale",
  "Import/Export",
  "Other",
];

export const GST_FILING_FREQUENCIES = [
  "Monthly",
  "Quarterly",
];

export const GST_COMPLIANCE_STATUSES = [
  "Regular",
  "Irregular",
  "Defaulter",
];

export const NOMINEE_RELATIONSHIPS = [
  "Spouse",
  "Father",
  "Mother",
  "Son",
  "Daughter",
  "Brother",
  "Sister",
  "Business Partner",
  "Other",
];

// ═══════ Invoice Types ═══════

export interface InvoiceItem {
  description: string;
  hsn_sac_code: string;
  quantity: number;
  unit: string;
  unit_price: number;
  discount_percent: number;
  gst_rate: number;
  cess_rate: number;
}

export interface InvoiceItemResponse extends InvoiceItem {
  id: number;
  item_number: number;
  discount_amount: number;
  taxable_value: number;
  cgst_amount: number;
  sgst_amount: number;
  igst_amount: number;
  cess_amount: number;
  total_amount: number;
}

export interface InvoiceCreate {
  invoice_date: string;
  due_date: string;
  supply_type: string;
  place_of_supply: string;
  reverse_charge: boolean;
  buyer_name: string;
  buyer_gstin?: string;
  buyer_address: string;
  buyer_city: string;
  buyer_state: string;
  buyer_pincode: string;
  buyer_phone?: string;
  buyer_email?: string;
  notes?: string;
  terms?: string;
  payment_status?: string;  // "paid" or "unpaid"
  items: InvoiceItem[];
}

export interface InvoiceResponse {
  id: number;
  vendor_id: number;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  supply_type: string;
  place_of_supply: string;
  place_of_supply_code: string;
  reverse_charge: boolean;
  buyer_name: string;
  buyer_gstin: string | null;
  buyer_address: string;
  buyer_city: string;
  buyer_state: string;
  buyer_state_code: string;
  buyer_pincode: string;
  buyer_phone: string | null;
  buyer_email: string | null;
  subtotal: number;
  total_cgst: number;
  total_sgst: number;
  total_igst: number;
  total_cess: number;
  total_discount: number;
  round_off: number;
  grand_total: number;
  notes: string | null;
  terms: string | null;
  invoice_status: string;
  payment_status: string;
  blockchain_hash: string | null;
  block_index: number | null;
  is_listed: boolean;
  items: InvoiceItemResponse[];
}

export interface InvoiceListItem {
  id: number;
  vendor_id: number;
  invoice_number: string;
  invoice_date: string;
  due_date: string;
  buyer_name: string;
  grand_total: number;
  invoice_status: string;
  payment_status: string;
  is_listed: boolean;
  blockchain_hash: string | null;
}

// ═══════ Marketplace Types ═══════

/** What lenders see when browsing */
export interface MarketplaceBrowseItem {
  id: number;
  invoice_id: number;
  listing_title: string | null;
  listing_description: string | null;
  vendor_name: string;
  business_name: string;
  business_type: string | null;
  business_category: string | null;
  business_description: string | null;
  business_city: string | null;
  business_state: string | null;
  business_images: string[];
  year_of_establishment: number | null;
  number_of_employees: number | null;
  profile_status: string | null;
  cibil_score: number | null;
  annual_turnover: number | null;
  total_reviews: number;
  average_rating: number;
  requested_amount: number;
  max_interest_rate: number;
  repayment_period_days: number;
  listing_status: string;
  risk_score: number | null;
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;
  grand_total: number | null;
  blockchain_hash: string | null;
  created_at: string | null;
  funded_amount: number | null;
  total_funded_deals: number;

  // Community Pot / Fractional Funding
  total_funded_amount: number;
  total_investors: number;
  min_investment: number;
  funding_progress_pct: number;
  remaining_amount: number;
}

/** Full detail when lender clicks a listing */
export interface MarketplaceDetailItem {
  id: number;
  invoice_id: number;
  vendor_id: number;
  listing_title: string | null;
  listing_description: string | null;
  vendor_name: string;
  business_name: string;
  business_type: string | null;
  business_category: string | null;
  business_description: string | null;
  business_city: string | null;
  business_state: string | null;
  business_images: string[];
  year_of_establishment: number | null;
  number_of_employees: number | null;
  vendor_gstin: string | null;
  vendor_state: string | null;
  profile_status: string | null;
  cibil_score: number | null;
  annual_turnover: number | null;
  monthly_revenue: number | null;
  risk_score: number | null;
  existing_liabilities: number | null;
  total_reviews: number;
  average_rating: number;
  total_funded_deals: number;
  gst_filing_frequency: string | null;
  total_gst_filings: number | null;
  gst_compliance_status: string | null;
  requested_percentage: number;
  requested_amount: number;
  discount_rate: number | null;
  max_interest_rate: number;
  repayment_period_days: number;
  listing_status: string;
  blockchain_hash: string | null;
  pdf_hash: string | null;
  invoice_number: string | null;
  invoice_date: string | null;
  due_date: string | null;
  grand_total: number | null;
  buyer_name: string | null;
  buyer_gstin: string | null;
  supply_type: string | null;
  funded_amount: number | null;
  funded_by: string | null;
  funded_at: string | null;

  // Community Pot / Fractional Funding
  total_funded_amount: number;
  total_investors: number;
  min_investment: number;
  funding_progress_pct: number;
  remaining_amount: number;
  investors: FractionalInvestor[] | null;

  created_at: string | null;
}

/** Fractional investor in Community Pot */
export interface FractionalInvestor {
  id: number;
  lender_id: number;
  lender_name: string;
  lender_type: string;
  organization: string | null;
  invested_amount: number;
  offered_interest_rate: number;
  ownership_percentage: number;
  expected_return: number | null;
  invested_at: string | null;
  blockchain_hash: string | null;
}

/** Lender entity */
export interface LenderResponse {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  organization: string | null;
  lender_type: string;
  created_at: string | null;
}

// ═══════ Verification Types ═══════

export interface VerificationCheckDetail {
  check: string;
  status: string;
  message: string;
}

export interface VerificationCheck {
  id: number;
  check_type: string;
  status: string;
  details: {
    checks?: VerificationCheckDetail[];
    [key: string]: unknown;
  };
  checked_at: string | null;
}

export interface VerificationResult {
  vendor_id: number;
  profile_status: string;
  checks: VerificationCheck[];
}

// ═══════ Constants ═══════

export const GST_RATES = [0, 5, 12, 18, 28];

export const UNITS = [
  "NOS", "KGS", "LTR", "MTR", "SQM", "SQF",
  "PCS", "BOX", "SET", "BAG", "TON", "QTL", "DOZ", "PAR", "UNT",
];

// ═══════ AI Negotiator Chat Types ═══════

export interface NegotiationChatMessage {
  id: number;
  sender: "lender" | "ai_agent" | "system";
  message: string;
  message_type: "offer" | "counter" | "accept" | "reject" | "info" | "welcome";
  offered_rate: number | null;
  offered_amount: number | null;
  funding_percentage: number | null;
  offer_score: number | null;
  created_at: string | null;
}

export interface NegotiationChat {
  session_id: number;
  listing_id: number;
  status: "active" | "accepted" | "rejected" | "expired";
  current_round: number;
  max_rounds: number;

  lender: {
    id: number;
    name: string;
    type: string;
    organization: string | null;
  };
  vendor: {
    id: number;
    business_name: string;
  };

  invoice_amount: number;
  remaining_amount: number;
  total_funded: number;
  total_investors: number;
  min_investment: number;
  vendor_credit_score: number;
  vendor_risk_grade: string;
  fair_market_rate: number;
  max_interest_rate: number;
  tenure_days: number;

  final_rate: number | null;
  final_amount: number | null;
  final_score: number | null;

  messages: NegotiationChatMessage[];

  // Extra fields for vendor/lender listing views
  invoice_number?: string;
  listing_status?: string;

  completed_at: string | null;
  created_at: string | null;
}

// ═══════ Direct Chat Types ═══════

export interface ChatConversation {
  id: number;
  other_user_id: number;
  other_user_name: string;
  other_user_role: string;
  subject: string | null;
  last_message: string | null;
  last_message_at: string | null;
  unread_count: number;
  listing_id: number | null;
  invoice_id: number | null;
  created_at: string;
}

export interface ChatMessage {
  id: number;
  conversation_id: number;
  sender_user_id: number;
  message: string;
  message_type: "text" | "offer" | "system" | "attachment";
  attachment_url: string | null;
  is_read: boolean;
  created_at: string;
}

export interface ChatAvailableUser {
  id: number;
  name: string;
  email: string;
  role: string;
  vendor_id: number | null;
  lender_id: number | null;
  business_name: string | null;
  organization: string | null;
}

// ═══════ Auth Types ═══════

export interface AuthUser {
  id: number;
  name: string;
  email: string;
  phone: string | null;
  role: "vendor" | "lender" | "admin";
  vendor_id: number | null;
  lender_id: number | null;
  is_verified: boolean;
  created_at: string | null;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: AuthUser;
}

// ═══════ Notification Types ═══════

export interface NotificationItem {
  id: number;
  user_id: number;
  title: string;
  message: string;
  notification_type: string;
  is_read: boolean;
  link: string | null;
  created_at: string | null;
}

// ═══════ Activity Types ═══════

export interface ActivityItem {
  id: number;
  entity_type: string;
  entity_id: number;
  action: string;
  description: string;
  user_id: number | null;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
}

// ═══════ Repayment Types ═══════

export interface RepaymentInstallment {
  id: number;
  installment_number: number;
  due_date: string;
  principal_amount: number;
  interest_amount: number;
  total_amount: number;
  status: string;
  paid_date: string | null;
  paid_amount: number | null;
}

export interface RepaymentSchedule {
  listing_id: number;
  listing_status: string;
  funded_amount: number | null;
  total_installments: number;
  installments: RepaymentInstallment[];
}

// ═══════ Dashboard Types ═══════

export interface VendorDashboardData {
  vendor: {
    id: number;
    name: string;
    business_name: string;
    profile_status: string;
    risk_score: number | null;
    cibil_score: number;
  };
  invoices: {
    total: number;
    total_value: number;
    paid: number;
    overdue: number;
    draft: number;
    listed: number;
    status_distribution: Record<string, number>;
  };
  marketplace: {
    total_listings: number;
    open: number;
    funded_count: number;
    settled_count: number;
    total_funded: number;
    total_settled: number;
  };
  repayment: {
    pending_amount: number;
    paid_amount: number;
    overdue_installments: number;
  };
  verification: {
    total_checks: number;
    passed: number;
    failed: number;
    warning: number;
    pending: number;
  };
  monthly_trend: { month: string; invoices: number; invoice_value: number; funded: number }[];
  recent_activity: ActivityItem[];
}

export interface LenderDashboardData {
  lender: {
    id: number;
    name: string;
    organization: string | null;
    lender_type: string;
  };
  portfolio: {
    total_investments: number;
    total_funded: number;
    active_investments: number;
    settled_investments: number;
    total_returns: number;
    roi_percent: number;
  };
  wallet: {
    balance: number;
    escrow_locked: number;
    total_withdrawn: number;
  };
  available_market: {
    listings_count: number;
    total_value: number;
  };
  risk_distribution: Record<string, number>;
  business_type_distribution: Record<string, number>;
  monthly_trend: { month: string; funded: number; settled: number; count: number }[];
  upcoming_repayments: { listing_id: number; installment: number; due_date: string; amount: number }[];
  recent_activity: ActivityItem[];
}

"""
Seed route — populates the database with realistic Indian MSME demo data.
10 MSME Vendors (Micro/Small/Medium), 10 MSME-focused Lenders,
invoices, marketplace listings, verification checks, credit scores — all pre-filled.

MSME Classification (Indian MSME Act 2020):
  Micro  → Investment ≤ ₹1 Cr, Turnover ≤ ₹5 Cr
  Small  → Investment ≤ ₹10 Cr, Turnover ≤ ₹50 Cr
  Medium → Investment ≤ ₹50 Cr, Turnover ≤ ₹250 Cr
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from models import (
    Vendor, Invoice, InvoiceItem, Lender, MarketplaceListing,
    VerificationCheck, User, CreditScore, Notification, ActivityLog,
    RepaymentSchedule, FractionalInvestment,
)
from blockchain import add_block
from datetime import datetime, timezone, timedelta
import bcrypt
import json
import random

router = APIRouter(prefix="/api/seed", tags=["Seed / Demo"])


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


DEMO_PASSWORD = "Demo@1234"

# ══════════════════════════════════════════════════════════
#  10 MSME DEMO VENDORS — Micro / Small / Medium
# ══════════════════════════════════════════════════════════

DEMO_VENDORS = [
    # ── V1: MICRO — Handloom Weaver, Varanasi (Manufacturing) ──
    {
        "full_name": "Lakshmi Devi Sahu",
        "date_of_birth": "1980-04-15",
        "phone": "9415678901",
        "email": "lakshmi.handloom@gmail.com",
        "personal_pan": "BHDPS4567K",
        "personal_aadhaar": "234567890123",
        "address": "Gali No 5, Lallapura, Varanasi",
        "city": "Varanasi",
        "state": "Uttar Pradesh",
        "pincode": "221001",
        "business_name": "Sahu Handloom & Banarasi Sarees",
        "business_type": "Proprietorship",
        "business_category": "Textiles & Handloom",
        "business_registration_number": "UP-PROP-2016-45321",
        "udyam_registration_number": "UDYAM-UP-09-0054321",
        "year_of_establishment": 2016,
        "number_of_employees": 6,
        "business_address": "Workshop 5, Lallapura Handloom Cluster",
        "business_city": "Varanasi",
        "business_state": "Uttar Pradesh",
        "business_pincode": "221001",
        "gstin": "09BHDPS4567K1Z8",
        "gst_registration_date": "2018-01-01",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 32,
        "gst_compliance_status": "Regular",
        "cibil_score": 695,
        "annual_turnover": 2400000,
        "monthly_revenue": 200000,
        "business_assets_value": 800000,
        "existing_liabilities": 650000,
        "bank_account_number": "10234567890",
        "bank_name": "State Bank of India",
        "bank_ifsc": "SBIN0002345",
        "bank_branch": "Godowlia, Varanasi",
        "nominee_name": "Ram Prasad Sahu",
        "nominee_relationship": "Husband",
        "nominee_phone": "9415678902",
        "nominee_aadhaar": "234567890124",
        "profile_status": "verified",
        "risk_score": 84,
        "business_description": "Traditional Banarasi silk and cotton saree weaving. GI-tagged handloom products. Supplies to Fab India, Taneira. 4 pit looms, 6 artisans. Micro Enterprise under MSME Act.",
        "verification_notes": "Udyam Micro. All govt checks passed. GST Regular. CIBIL 695.",
    },
    # ── V2: MICRO — Agri-Food Processor, Nashik (Manufacturing) ──
    {
        "full_name": "Rajesh Baban Patil",
        "date_of_birth": "1985-08-22",
        "phone": "9823456789",
        "email": "rajesh.agrofoods@gmail.com",
        "personal_pan": "CVKRP5678L",
        "personal_aadhaar": "567890123456",
        "address": "Plot 12, MIDC Sinnar, Nashik",
        "city": "Nashik",
        "state": "Maharashtra",
        "pincode": "422103",
        "business_name": "Patil Agro Foods",
        "business_type": "Proprietorship",
        "business_category": "Food Processing",
        "business_registration_number": "MH-PROP-2019-78654",
        "udyam_registration_number": "UDYAM-MH-27-0078654",
        "year_of_establishment": 2019,
        "number_of_employees": 8,
        "business_address": "Plot 12, MIDC Sinnar, Nashik Industrial Area",
        "business_city": "Nashik",
        "business_state": "Maharashtra",
        "business_pincode": "422103",
        "gstin": "27CVKRP5678L1Z6",
        "gst_registration_date": "2019-07-01",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 16,
        "gst_compliance_status": "Irregular",
        "cibil_score": 640,
        "annual_turnover": 3600000,
        "monthly_revenue": 300000,
        "business_assets_value": 950000,
        "existing_liabilities": 1200000,
        "bank_account_number": "20345678901",
        "bank_name": "Bank of Maharashtra",
        "bank_ifsc": "MAHB0001234",
        "bank_branch": "Nashik Road",
        "nominee_name": "Sunita Patil",
        "nominee_relationship": "Wife",
        "nominee_phone": "9823456790",
        "nominee_aadhaar": "567890123457",
        "profile_status": "verified",
        "risk_score": 46,
        "business_description": "Dehydrated onion & garlic flakes, tomato powder, and spice blends. FSSAI licensed. Exports to Middle East through APEDA. Micro Enterprise.",
        "verification_notes": "Udyam Micro. FSSAI compliant. GST Irregular — 3 missed filings. CIBIL 640.",
    },
    # ── V3: MICRO — Leather Goods, Agra (Manufacturing) ──
    {
        "full_name": "Mohammed Irfan Qureshi",
        "date_of_birth": "1990-01-10",
        "phone": "9897654321",
        "email": "irfan.leather@gmail.com",
        "personal_pan": "FQKPM7890P",
        "personal_aadhaar": "012345678901",
        "address": "Belanganj, Agra",
        "city": "Agra",
        "state": "Uttar Pradesh",
        "pincode": "282004",
        "business_name": "Qureshi Leather Craft",
        "business_type": "Proprietorship",
        "business_category": "Leather & Footwear",
        "business_registration_number": "UP-PROP-2020-09876",
        "udyam_registration_number": "UDYAM-UP-09-0091234",
        "year_of_establishment": 2020,
        "number_of_employees": 5,
        "business_address": "Shop 22, Belanganj Leather Market, Agra",
        "business_city": "Agra",
        "business_state": "Uttar Pradesh",
        "business_pincode": "282004",
        "gstin": "09FQKPM7890P1Z7",
        "gst_registration_date": "2020-04-01",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 24,
        "gst_compliance_status": "Regular",
        "cibil_score": 580,
        "annual_turnover": 1800000,
        "monthly_revenue": 150000,
        "business_assets_value": 450000,
        "existing_liabilities": 120000,
        "bank_account_number": "50678901234",
        "bank_name": "Union Bank of India",
        "bank_ifsc": "UBIN0534567",
        "bank_branch": "Belanganj, Agra",
        "nominee_name": "Shabana Qureshi",
        "nominee_relationship": "Wife",
        "nominee_phone": "9897654322",
        "nominee_aadhaar": "123456789012",
        "profile_status": "verified",
        "risk_score": 66,
        "business_description": "Handcrafted leather bags, wallets, and belts. Supplies to Amazon Karigar, Flipkart Samarth. Micro Enterprise, KVIC certified artisan cluster.",
        "verification_notes": "Udyam Micro. GST Regular. CIBIL 580. First-gen entrepreneur.",
    },
    # ── V4: SMALL — Auto Component Manufacturer, Pune (Manufacturing) ──
    {
        "full_name": "Ganesh Pramod Pawar",
        "date_of_birth": "1975-09-18",
        "phone": "9822334455",
        "email": "ganesh.autocomp@gmail.com",
        "personal_pan": "EKGPP7534N",
        "personal_aadhaar": "456789012345",
        "address": "Survey No 23, Bhosari MIDC",
        "city": "Pune",
        "state": "Maharashtra",
        "pincode": "411026",
        "business_name": "Pawar Auto Components Pvt Ltd",
        "business_type": "Pvt Ltd",
        "business_category": "Auto Components Manufacturing",
        "business_registration_number": "MH-PVT-2010-56789",
        "udyam_registration_number": "UDYAM-MH-27-0056789",
        "year_of_establishment": 2010,
        "number_of_employees": 42,
        "business_address": "Survey No 23, Plot 8, Bhosari MIDC Pune",
        "business_city": "Pune",
        "business_state": "Maharashtra",
        "business_pincode": "411026",
        "gstin": "27EKGPP7534N1Z5",
        "gst_registration_date": "2017-07-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 103,
        "gst_compliance_status": "Regular",
        "cibil_score": 720,
        "annual_turnover": 85000000,
        "monthly_revenue": 7083333,
        "business_assets_value": 45000000,
        "existing_liabilities": 30000000,
        "bank_account_number": "50234567890",
        "bank_name": "ICICI Bank",
        "bank_ifsc": "ICIC0001234",
        "bank_branch": "Ajmera, Pimpri-Chinchwad",
        "nominee_name": "Seema Pawar",
        "nominee_relationship": "Wife",
        "nominee_phone": "9822334456",
        "nominee_aadhaar": "456789012346",
        "profile_status": "verified",
        "risk_score": 87,
        "business_description": "OEM brake pads, gaskets, and engine mounts. Tier-2 supplier to Tata Motors, Bajaj Auto. ISO 9001:2015 certified. IATF 16949 in progress. Small Enterprise under MSME Act.",
        "verification_notes": "Udyam Small Enterprise. CIBIL 720. Good credit. High working capital debt. Monthly GST filer.",
    },
    # ── V5: SMALL — Textile Exporter, Tirupur (Manufacturing) ──
    {
        "full_name": "Karthik Sundaram Rajan",
        "date_of_birth": "1982-06-05",
        "phone": "9443567890",
        "email": "karthik.textiles@gmail.com",
        "personal_pan": "DQRKS5678R",
        "personal_aadhaar": "345678901234",
        "address": "Avinashi Road, Tirupur",
        "city": "Tirupur",
        "state": "Tamil Nadu",
        "pincode": "641602",
        "business_name": "Rajan Knit Exports",
        "business_type": "Partnership",
        "business_category": "Garment & Knitwear Export",
        "business_registration_number": "TN-PART-2012-34567",
        "udyam_registration_number": "UDYAM-TN-33-0034567",
        "year_of_establishment": 2012,
        "number_of_employees": 65,
        "business_address": "Plot 45-46, SIPCOT Industrial Complex, Tirupur",
        "business_city": "Tirupur",
        "business_state": "Tamil Nadu",
        "business_pincode": "641602",
        "gstin": "33DQRKS5678R1Z2",
        "gst_registration_date": "2017-07-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 103,
        "gst_compliance_status": "Regular",
        "cibil_score": 735,
        "annual_turnover": 120000000,
        "monthly_revenue": 10000000,
        "business_assets_value": 35000000,
        "existing_liabilities": 42000000,
        "bank_account_number": "40123456789",
        "bank_name": "Indian Bank",
        "bank_ifsc": "IDIB000T567",
        "bank_branch": "Avinashi Road, Tirupur",
        "nominee_name": "Priya Rajan",
        "nominee_relationship": "Wife",
        "nominee_phone": "9443567891",
        "nominee_aadhaar": "345678901235",
        "profile_status": "verified",
        "risk_score": 87,
        "business_description": "Cotton knitwear & T-shirt export. Major buyers: H&M, Decathlon, Primark. Oeko-Tex and GOTS certified. 65 employees. Small Enterprise under MSME Act.",
        "verification_notes": "Udyam Small. Good compliance. 103 Monthly GST filings. CIBIL 735. High debt-to-turnover ratio.",
    },
    # ── V6: MICRO — IT Services, Indore (Services) ──
    {
        "full_name": "Priya Sharma",
        "date_of_birth": "1993-03-25",
        "phone": "9752345678",
        "email": "priya.itservices@gmail.com",
        "personal_pan": "DMKPS9312F",
        "personal_aadhaar": "678901234567",
        "address": "203, Sapna Sangeeta Road, Indore",
        "city": "Indore",
        "state": "Madhya Pradesh",
        "pincode": "452001",
        "business_name": "PixelCraft Digital Solutions",
        "business_type": "LLP",
        "business_category": "IT & Software Services",
        "business_registration_number": "MP-LLP-2021-67890",
        "udyam_registration_number": "UDYAM-MP-23-0067890",
        "year_of_establishment": 2021,
        "number_of_employees": 10,
        "business_address": "Floor 2, Sapna Tower, Sapna Sangeeta Road",
        "business_city": "Indore",
        "business_state": "Madhya Pradesh",
        "business_pincode": "452001",
        "gstin": "23DMKPS9312F1Z5",
        "gst_registration_date": "2021-07-01",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 14,
        "gst_compliance_status": "Regular",
        "cibil_score": 720,
        "annual_turnover": 4500000,
        "monthly_revenue": 375000,
        "business_assets_value": 600000,
        "existing_liabilities": 100000,
        "bank_account_number": "30567890123",
        "bank_name": "Kotak Mahindra Bank",
        "bank_ifsc": "KKBK0007890",
        "bank_branch": "Sapna Sangeeta, Indore",
        "nominee_name": "Amit Sharma",
        "nominee_relationship": "Husband",
        "nominee_phone": "9752345679",
        "nominee_aadhaar": "678901234568",
        "profile_status": "verified",
        "risk_score": 74,
        "business_description": "Web development, mobile apps, and UX design for SMEs. Clients: 15+ local businesses and 3 export houses. Micro Enterprise — IT services sector.",
        "verification_notes": "Udyam Micro (Services). GST Regular. CIBIL 720. Woman entrepreneur.",
    },
    # ── V7: SMALL — Pharma Formulations, Hyderabad (Manufacturing) ──
    {
        "full_name": "Venkatesh Reddy Gundla",
        "date_of_birth": "1978-11-08",
        "phone": "9848012345",
        "email": "venkatesh.pharma@gmail.com",
        "personal_pan": "HLKPV8012R",
        "personal_aadhaar": "789012345678",
        "address": "Bachupally Pharma City, Hyderabad",
        "city": "Hyderabad",
        "state": "Telangana",
        "pincode": "500090",
        "business_name": "GV Pharma Formulations Pvt Ltd",
        "business_type": "Pvt Ltd",
        "business_category": "Pharmaceutical Manufacturing",
        "business_registration_number": "TS-PVT-2014-89012",
        "udyam_registration_number": "UDYAM-TS-36-0089012",
        "year_of_establishment": 2014,
        "number_of_employees": 55,
        "business_address": "Plot 34, Phase II, Bachupally Pharma SEZ",
        "business_city": "Hyderabad",
        "business_state": "Telangana",
        "business_pincode": "500090",
        "gstin": "36HLKPV8012R1Z8",
        "gst_registration_date": "2017-07-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 103,
        "gst_compliance_status": "Regular",
        "cibil_score": 730,
        "annual_turnover": 150000000,
        "monthly_revenue": 12500000,
        "business_assets_value": 40000000,
        "existing_liabilities": 52000000,
        "bank_account_number": "80678901234",
        "bank_name": "HDFC Bank",
        "bank_ifsc": "HDFC0001234",
        "bank_branch": "Kukatpally, Hyderabad",
        "nominee_name": "Lakshmi Reddy",
        "nominee_relationship": "Wife",
        "nominee_phone": "9848012346",
        "nominee_aadhaar": "789012345679",
        "profile_status": "verified",
        "risk_score": 87,
        "business_description": "WHO-GMP certified pharma unit. Paracetamol, antibiotics, ORS sachets. Exports to 12 African countries. 55 employees. Small Enterprise — Manufacturing.",
        "verification_notes": "Udyam Small. CIBIL 730. WHO-GMP certified. Monthly GST filer. Medium debt-to-turnover.",
    },
    # ── V8: MEDIUM — Steel Fabrication, Jamshedpur (Manufacturing) ──
    {
        "full_name": "Ajay Kumar Singh",
        "date_of_birth": "1968-07-20",
        "phone": "9431234567",
        "email": "ajay.steelfab@gmail.com",
        "personal_pan": "GKLAS6823M",
        "personal_aadhaar": "890123456789",
        "address": "Adityapur Industrial Area, Jamshedpur",
        "city": "Jamshedpur",
        "state": "Jharkhand",
        "pincode": "831013",
        "business_name": "Singh Steel Fabricators Ltd",
        "business_type": "Pvt Ltd",
        "business_category": "Steel & Metal Fabrication",
        "business_registration_number": "JH-PVT-2005-12345",
        "udyam_registration_number": "UDYAM-JH-20-0012345",
        "year_of_establishment": 2005,
        "number_of_employees": 120,
        "business_address": "Plot 78, Adityapur Industrial Area, Phase II",
        "business_city": "Jamshedpur",
        "business_state": "Jharkhand",
        "business_pincode": "831013",
        "gstin": "20GKLAS6823M1Z4",
        "gst_registration_date": "2017-07-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 103,
        "gst_compliance_status": "Regular",
        "cibil_score": 760,
        "annual_turnover": 480000000,
        "monthly_revenue": 40000000,
        "business_assets_value": 150000000,
        "existing_liabilities": 180000000,
        "bank_account_number": "60456789012",
        "bank_name": "Axis Bank",
        "bank_ifsc": "UTIB0001234",
        "bank_branch": "Bistupur, Jamshedpur",
        "nominee_name": "Suman Singh",
        "nominee_relationship": "Wife",
        "nominee_phone": "9431234568",
        "nominee_aadhaar": "890123456790",
        "profile_status": "verified",
        "risk_score": 97,
        "business_description": "Structural steel fabrication for bridges, railway coaches, and industrial sheds. Supplies to SAIL, L&T, Tata Projects. ISO 3834 welding cert. 120 employees. Medium Enterprise.",
        "verification_notes": "Udyam Medium. 20-year track record. CIBIL 760. Good credit. 37.5% debt-to-turnover.",
    },
    # ── V9: MICRO — Artisan Pottery, Khurja (Manufacturing) ──
    {
        "full_name": "Razia Begum",
        "date_of_birth": "1987-05-12",
        "phone": "9412345678",
        "email": "razia.pottery@gmail.com",
        "personal_pan": "HRKPB3456Q",
        "personal_aadhaar": "901234567890",
        "address": "Pottery Colony, Khurja",
        "city": "Khurja",
        "state": "Uttar Pradesh",
        "pincode": "203131",
        "business_name": "Khurja Ceramic Arts",
        "business_type": "Proprietorship",
        "business_category": "Ceramics & Pottery",
        "business_registration_number": "UP-PROP-2018-23456",
        "udyam_registration_number": "UDYAM-UP-09-0023456",
        "year_of_establishment": 2018,
        "number_of_employees": 4,
        "business_address": "Pottery Colony Lane 3, Khurja Ceramic Cluster",
        "business_city": "Khurja",
        "business_state": "Uttar Pradesh",
        "business_pincode": "203131",
        "gstin": "09HRKPB3456Q1Z3",
        "gst_registration_date": "2019-01-01",
        "gst_filing_frequency": "Quarterly",
        "total_gst_filings": 28,
        "gst_compliance_status": "Regular",
        "cibil_score": 610,
        "annual_turnover": 1200000,
        "monthly_revenue": 100000,
        "business_assets_value": 350000,
        "existing_liabilities": 480000,
        "bank_account_number": "70567890123",
        "bank_name": "Punjab National Bank",
        "bank_ifsc": "PUNB0123400",
        "bank_branch": "Khurja, Bulandshahr",
        "nominee_name": "Saleem Ahmad",
        "nominee_relationship": "Husband",
        "nominee_phone": "9412345679",
        "nominee_aadhaar": "901234567891",
        "profile_status": "verified",
        "risk_score": 63,
        "business_description": "GI-tagged Khurja pottery. Handpainted ceramic mugs, plates, planters. Major buyer: Chumbak, Nykaa Home. 4 artisans. Micro Enterprise — KVIC cluster.",
        "verification_notes": "Udyam Micro. GI-tag certified. CIBIL 610. High debt relative to turnover. Artisan cluster member.",
    },
    # ── V10: SMALL — Electronics Assembly, Noida (Manufacturing) ──
    {
        "full_name": "Deepak Chandra Gupta",
        "date_of_birth": "1980-12-30",
        "phone": "9810567890",
        "email": "deepak.electronics@gmail.com",
        "personal_pan": "JLKGD8901S",
        "personal_aadhaar": "123098765432",
        "address": "Sector 63, Noida",
        "city": "Noida",
        "state": "Uttar Pradesh",
        "pincode": "201301",
        "business_name": "DCG Electronics Manufacturing",
        "business_type": "Pvt Ltd",
        "business_category": "Electronics Manufacturing",
        "business_registration_number": "UP-PVT-2015-34567",
        "udyam_registration_number": "UDYAM-UP-09-0034567",
        "year_of_establishment": 2015,
        "number_of_employees": 38,
        "business_address": "C-45, Sector 63, Noida Industrial Area",
        "business_city": "Noida",
        "business_state": "Uttar Pradesh",
        "business_pincode": "201301",
        "gstin": "09JLKGD8901S1Z1",
        "gst_registration_date": "2017-07-01",
        "gst_filing_frequency": "Monthly",
        "total_gst_filings": 103,
        "gst_compliance_status": "Regular",
        "cibil_score": 740,
        "annual_turnover": 95000000,
        "monthly_revenue": 7916667,
        "business_assets_value": 28000000,
        "existing_liabilities": 8000000,
        "bank_account_number": "90789012345",
        "bank_name": "Yes Bank",
        "bank_ifsc": "YESB0001234",
        "bank_branch": "Sector 18, Noida",
        "nominee_name": "Kavita Gupta",
        "nominee_relationship": "Wife",
        "nominee_phone": "9810567891",
        "nominee_aadhaar": "123098765433",
        "profile_status": "verified",
        "risk_score": 90,
        "business_description": "PCB assembly, LED driver modules, IoT sensor boards. Clients: Havells, Syska, govt smart-city projects. PLI scheme beneficiary. Small Enterprise — Manufacturing.",
        "verification_notes": "Udyam Small. CIBIL 740. Monthly GST filer. PLI registered.",
    },
]


# ══════════════════════════════════════════════════════════
#  10 MSME-FOCUSED LENDERS
# ══════════════════════════════════════════════════════════

DEMO_LENDERS = [
    {"name": "Ramesh Gupta", "email": "ramesh@sidbi-partner.in", "phone": "9811111111", "organization": "SIDBI Micro Finance Partner", "lender_type": "nbfc", "wallet_balance": 5000000},
    {"name": "Meena Patel", "email": "meena.patel@mudrafund.in", "phone": "9822222222", "organization": "Mudra Loan Facilitator", "lender_type": "nbfc", "wallet_balance": 3000000},
    {"name": "Harish Bansal", "email": "harish@sahayakfund.in", "phone": "9833333333", "organization": "Sahayak MSME Fund", "lender_type": "nbfc", "wallet_balance": 8000000},
    {"name": "Suresh Iyer", "email": "suresh.iyer@gmail.com", "phone": "9844444444", "organization": None, "lender_type": "individual", "wallet_balance": 1000000},
    {"name": "Kavita Singh", "email": "kavita@msmenivesh.com", "phone": "9855555555", "organization": "MSME Nivesh Capital", "lender_type": "nbfc", "wallet_balance": 10000000},
    {"name": "Arun Menon", "email": "arun@fintechmsme.in", "phone": "9866666666", "organization": "FinTech MSME Ventures", "lender_type": "nbfc", "wallet_balance": 7500000},
    {"name": "Anita Deshmukh", "email": "anita.d@gmail.com", "phone": "9877777777", "organization": None, "lender_type": "individual", "wallet_balance": 500000},
    {"name": "Mohd Farooq", "email": "farooq@crescentcapital.in", "phone": "9888888888", "organization": "Crescent MSME Partners", "lender_type": "nbfc", "wallet_balance": 6000000},
    {"name": "Pooja Agarwal", "email": "pooja.ag@udyamgrow.in", "phone": "9899999999", "organization": "Udyam Growth Advisors", "lender_type": "nbfc", "wallet_balance": 4000000},
    {"name": "Vikram Choudhary", "email": "vikram.ch@gmail.com", "phone": "9800012345", "organization": None, "lender_type": "individual", "wallet_balance": 750000},
]


# ══════════════════════════════════════════════════════════
#  DEMO USER ACCOUNTS — linked to vendors/lenders
# ══════════════════════════════════════════════════════════

DEMO_USERS = [
    # 10 Vendor accounts
    {"name": "Lakshmi Devi Sahu", "email": "vendor1@invox.demo", "phone": "9415678901", "role": "vendor", "vendor_idx": 0},
    {"name": "Rajesh Baban Patil", "email": "vendor2@invox.demo", "phone": "9823456789", "role": "vendor", "vendor_idx": 1},
    {"name": "Mohammed Irfan Qureshi", "email": "vendor3@invox.demo", "phone": "9897654321", "role": "vendor", "vendor_idx": 2},
    {"name": "Ganesh Pramod Pawar", "email": "vendor4@invox.demo", "phone": "9822334455", "role": "vendor", "vendor_idx": 3},
    {"name": "Karthik Sundaram Rajan", "email": "vendor5@invox.demo", "phone": "9443567890", "role": "vendor", "vendor_idx": 4},
    {"name": "Priya Sharma", "email": "vendor6@invox.demo", "phone": "9752345678", "role": "vendor", "vendor_idx": 5},
    {"name": "Venkatesh Reddy Gundla", "email": "vendor7@invox.demo", "phone": "9848012345", "role": "vendor", "vendor_idx": 6},
    {"name": "Ajay Kumar Singh", "email": "vendor8@invox.demo", "phone": "9431234567", "role": "vendor", "vendor_idx": 7},
    {"name": "Razia Begum", "email": "vendor9@invox.demo", "phone": "9412345678", "role": "vendor", "vendor_idx": 8},
    {"name": "Deepak Chandra Gupta", "email": "vendor10@invox.demo", "phone": "9810567890", "role": "vendor", "vendor_idx": 9},
    # 10 Lender accounts
    {"name": "Ramesh Gupta", "email": "lender1@invox.demo", "phone": "9811111111", "role": "lender", "lender_idx": 0},
    {"name": "Meena Patel", "email": "lender2@invox.demo", "phone": "9822222222", "role": "lender", "lender_idx": 1},
    {"name": "Harish Bansal", "email": "lender3@invox.demo", "phone": "9833333333", "role": "lender", "lender_idx": 2},
    {"name": "Suresh Iyer", "email": "lender4@invox.demo", "phone": "9844444444", "role": "lender", "lender_idx": 3},
    {"name": "Kavita Singh", "email": "lender5@invox.demo", "phone": "9855555555", "role": "lender", "lender_idx": 4},
    {"name": "Arun Menon", "email": "lender6@invox.demo", "phone": "9866666666", "role": "lender", "lender_idx": 5},
    {"name": "Anita Deshmukh", "email": "lender7@invox.demo", "phone": "9877777777", "role": "lender", "lender_idx": 6},
    {"name": "Mohd Farooq", "email": "lender8@invox.demo", "phone": "9888888888", "role": "lender", "lender_idx": 7},
    {"name": "Pooja Agarwal", "email": "lender9@invox.demo", "phone": "9899999999", "role": "lender", "lender_idx": 8},
    {"name": "Vikram Choudhary", "email": "lender10@invox.demo", "phone": "9800012345", "role": "lender", "lender_idx": 9},
    # Admin + legacy alias
    {"name": "Admin InvoX", "email": "admin@invox.demo", "phone": "9800000000", "role": "admin"},
    {"name": "Ramesh Gupta", "email": "lender@invox.demo", "phone": "9811111112", "role": "lender", "lender_idx": 0},
]


# ══════════════════════════════════════════════════════════
#  MSME INVOICES (8 invoices — real MSME supply chains)
# ══════════════════════════════════════════════════════════

DEMO_INVOICES = [
    # V1 — Handloom sarees → FabIndia
    (0, {
        "invoice_number": "MSME-2026-001",
        "invoice_date": "2026-01-20",
        "due_date": "2026-03-20",
        "supply_type": "inter_state",
        "place_of_supply": "Delhi",
        "place_of_supply_code": "07",
        "reverse_charge": False,
        "buyer_name": "FabIndia Overseas Pvt Ltd",
        "buyer_gstin": "07AABCF1234R1Z9",
        "buyer_address": "N Block, Greater Kailash I",
        "buyer_city": "New Delhi",
        "buyer_state": "Delhi",
        "buyer_state_code": "07",
        "buyer_pincode": "110048",
        "buyer_phone": "9811023456",
        "buyer_email": "procurement@fabindia.in",
        "notes": "Banarasi silk sarees for Spring 2026 collection — Handloom Mark certified",
        "terms": "Net 60 days. Payment via RTGS. Quality inspection at destination.",
        "invoice_status": "issued",
        "items": [
            {"description": "Banarasi Silk Saree (Pure Katan)", "hsn_sac_code": "50072090", "quantity": 25, "unit": "PCS", "unit_price": 4500, "gst_rate": 5},
            {"description": "Banarasi Cotton Saree (Tanchoi)", "hsn_sac_code": "52091100", "quantity": 40, "unit": "PCS", "unit_price": 1800, "gst_rate": 5},
            {"description": "Brocade Dupatta Set (Silk Blend)", "hsn_sac_code": "50072090", "quantity": 30, "unit": "SET", "unit_price": 950, "gst_rate": 5},
            {"description": "Packaging & Courier (Insured)", "hsn_sac_code": "996812", "quantity": 1, "unit": "LOT", "unit_price": 3500, "gst_rate": 18},
        ],
    }),
    # V2 — Agro foods → D-Mart
    (1, {
        "invoice_number": "MSME-2026-002",
        "invoice_date": "2026-02-01",
        "due_date": "2026-03-15",
        "supply_type": "intra_state",
        "place_of_supply": "Maharashtra",
        "place_of_supply_code": "27",
        "reverse_charge": False,
        "buyer_name": "Avenue Supermarts Ltd (D-Mart)",
        "buyer_gstin": "27AABCA5678K1Z2",
        "buyer_address": "Magarpatta City, Hadapsar",
        "buyer_city": "Pune",
        "buyer_state": "Maharashtra",
        "buyer_state_code": "27",
        "buyer_pincode": "411028",
        "buyer_phone": "9823098765",
        "buyer_email": "vendor.relations@dmartindia.com",
        "notes": "Monthly supply of dehydrated vegetables — FSSAI Lic. 11521998000234",
        "terms": "COD on delivery confirmation. Net 30.",
        "invoice_status": "issued",
        "items": [
            {"description": "Dehydrated Onion Flakes (25kg bag)", "hsn_sac_code": "07129090", "quantity": 40, "unit": "BAG", "unit_price": 1200, "gst_rate": 5},
            {"description": "Dehydrated Garlic Granules (10kg)", "hsn_sac_code": "07129090", "quantity": 25, "unit": "BAG", "unit_price": 1800, "gst_rate": 5},
            {"description": "Tomato Powder (5kg pouch)", "hsn_sac_code": "07129090", "quantity": 30, "unit": "PKT", "unit_price": 650, "gst_rate": 5},
        ],
    }),
    # V3 — Leather bags → Amazon Karigar
    (2, {
        "invoice_number": "MSME-2026-003",
        "invoice_date": "2026-02-05",
        "due_date": "2026-03-05",
        "supply_type": "inter_state",
        "place_of_supply": "Karnataka",
        "place_of_supply_code": "29",
        "reverse_charge": False,
        "buyer_name": "Amazon Seller Services Pvt Ltd",
        "buyer_gstin": "29AABCA4321P1Z6",
        "buyer_address": "Embassy Golf Links, Domlur",
        "buyer_city": "Bengaluru",
        "buyer_state": "Karnataka",
        "buyer_state_code": "29",
        "buyer_pincode": "560071",
        "buyer_phone": "9945678901",
        "buyer_email": "karigar-support@amazon.in",
        "notes": "Amazon Karigar handcrafted leather collection — Feb batch",
        "terms": "Net 45 days. Return within 7 days for defects.",
        "invoice_status": "issued",
        "items": [
            {"description": "Handstitched Leather Messenger Bag", "hsn_sac_code": "42021210", "quantity": 50, "unit": "PCS", "unit_price": 1200, "gst_rate": 18},
            {"description": "Leather Bifold Wallet (Genuine)", "hsn_sac_code": "42023100", "quantity": 100, "unit": "PCS", "unit_price": 350, "gst_rate": 18},
            {"description": "Leather Belt (Full Grain, 38mm)", "hsn_sac_code": "42033000", "quantity": 80, "unit": "PCS", "unit_price": 280, "gst_rate": 18},
        ],
    }),
    # V4 — Auto components → Tata Motors
    (3, {
        "invoice_number": "MSME-2026-004",
        "invoice_date": "2026-02-01",
        "due_date": "2026-04-01",
        "supply_type": "intra_state",
        "place_of_supply": "Maharashtra",
        "place_of_supply_code": "27",
        "reverse_charge": False,
        "buyer_name": "Tata Motors Ltd — Pune Plant",
        "buyer_gstin": "27AABCT1332L1ZC",
        "buyer_address": "Pimpri-Chinchwad Industrial Area",
        "buyer_city": "Pune",
        "buyer_state": "Maharashtra",
        "buyer_state_code": "27",
        "buyer_pincode": "411018",
        "buyer_phone": "9822098765",
        "buyer_email": "purchase@tatamotors.com",
        "notes": "Monthly supply of brake components — Feb 2026. PO Ref: TML/PUN/2026/0045",
        "terms": "Net 45 days. Quality inspection before acceptance.",
        "invoice_status": "issued",
        "items": [
            {"description": "Brake Pad Set (Heavy Vehicle)", "hsn_sac_code": "87083010", "quantity": 200, "unit": "SET", "unit_price": 450, "gst_rate": 18},
            {"description": "Cylinder Head Gasket (Diesel)", "hsn_sac_code": "84841000", "quantity": 100, "unit": "PCS", "unit_price": 280, "gst_rate": 18},
            {"description": "Engine Mount (Rubber-Metal)", "hsn_sac_code": "40169390", "quantity": 150, "unit": "PCS", "unit_price": 320, "gst_rate": 18},
        ],
    }),
    # V5 — Knitwear → H&M India
    (4, {
        "invoice_number": "MSME-2026-005",
        "invoice_date": "2026-01-25",
        "due_date": "2026-03-25",
        "supply_type": "inter_state",
        "place_of_supply": "Karnataka",
        "place_of_supply_code": "29",
        "reverse_charge": False,
        "buyer_name": "H&M Hennes & Mauritz Retail Pvt Ltd",
        "buyer_gstin": "29AABCH5678M1Z4",
        "buyer_address": "Prestige Falcon Tower, Brigade Road",
        "buyer_city": "Bengaluru",
        "buyer_state": "Karnataka",
        "buyer_state_code": "29",
        "buyer_pincode": "560001",
        "buyer_phone": "9900123456",
        "buyer_email": "sourcing-india@hm.com",
        "notes": "SS26 Collection — Organic cotton T-shirts and polo shirts. GOTS certified.",
        "terms": "LC at sight. Quality as per AQL 2.5. Shipment by Feb 28.",
        "invoice_status": "issued",
        "items": [
            {"description": "Organic Cotton Round-Neck T-Shirt", "hsn_sac_code": "61091000", "quantity": 2000, "unit": "PCS", "unit_price": 180, "gst_rate": 5},
            {"description": "Polo T-Shirt (Cotton Pique)", "hsn_sac_code": "61051000", "quantity": 1500, "unit": "PCS", "unit_price": 250, "gst_rate": 5},
            {"description": "Printed Crew-Neck (Kids Range)", "hsn_sac_code": "61091000", "quantity": 1000, "unit": "PCS", "unit_price": 140, "gst_rate": 5},
        ],
    }),
    # V6 — IT services → Export house
    (5, {
        "invoice_number": "MSME-2026-006",
        "invoice_date": "2026-02-10",
        "due_date": "2026-03-10",
        "supply_type": "intra_state",
        "place_of_supply": "Madhya Pradesh",
        "place_of_supply_code": "23",
        "reverse_charge": False,
        "buyer_name": "IndoGerman Export House Pvt Ltd",
        "buyer_gstin": "23AABCI9876K1Z5",
        "buyer_address": "AB Road, Indore",
        "buyer_city": "Indore",
        "buyer_state": "Madhya Pradesh",
        "buyer_state_code": "23",
        "buyer_pincode": "452010",
        "buyer_phone": "9752098765",
        "buyer_email": "it@indogermanexports.com",
        "notes": "E-commerce website development + ERP integration — Phase 1",
        "terms": "50% advance paid. 50% on UAT sign-off. Net 15.",
        "invoice_status": "issued",
        "items": [
            {"description": "E-commerce Website (React + Node)", "hsn_sac_code": "998314", "quantity": 1, "unit": "LOT", "unit_price": 180000, "gst_rate": 18},
            {"description": "ERP Integration Module (Tally)", "hsn_sac_code": "998314", "quantity": 1, "unit": "LOT", "unit_price": 75000, "gst_rate": 18},
            {"description": "12-month AMC & Hosting", "hsn_sac_code": "998316", "quantity": 1, "unit": "LOT", "unit_price": 36000, "gst_rate": 18},
        ],
    }),
    # V7 — Pharma → Apollo Pharmacy
    (6, {
        "invoice_number": "MSME-2026-007",
        "invoice_date": "2026-02-05",
        "due_date": "2026-03-05",
        "supply_type": "inter_state",
        "place_of_supply": "Andhra Pradesh",
        "place_of_supply_code": "37",
        "reverse_charge": False,
        "buyer_name": "Apollo Pharmacy — Visakhapatnam Region",
        "buyer_gstin": "37AABCA1234H1Z2",
        "buyer_address": "Beach Road, Visakhapatnam",
        "buyer_city": "Visakhapatnam",
        "buyer_state": "Andhra Pradesh",
        "buyer_state_code": "37",
        "buyer_pincode": "530001",
        "buyer_phone": "9849876543",
        "buyer_email": "vizag@apollopharmacy.in",
        "notes": "Monthly pharma supplies — Feb 2026. Cold chain maintained.",
        "terms": "Net 30 days. Cold chain compliance mandatory.",
        "invoice_status": "issued",
        "items": [
            {"description": "Paracetamol 500mg (Box of 100)", "hsn_sac_code": "30049099", "quantity": 500, "unit": "BOX", "unit_price": 45, "gst_rate": 12},
            {"description": "Amoxicillin 250mg (Strip of 10)", "hsn_sac_code": "30041000", "quantity": 300, "unit": "PKT", "unit_price": 85, "gst_rate": 12},
            {"description": "ORS Sachets (Carton of 200)", "hsn_sac_code": "30049099", "quantity": 100, "unit": "CTN", "unit_price": 320, "gst_rate": 5},
            {"description": "Insulin Glargine 100IU (Pen)", "hsn_sac_code": "30043100", "quantity": 50, "unit": "PCS", "unit_price": 1200, "gst_rate": 5},
        ],
    }),
    # V8 — Steel → L&T
    (7, {
        "invoice_number": "MSME-2026-008",
        "invoice_date": "2026-01-15",
        "due_date": "2026-04-15",
        "supply_type": "inter_state",
        "place_of_supply": "Maharashtra",
        "place_of_supply_code": "27",
        "reverse_charge": False,
        "buyer_name": "Larsen & Toubro Ltd — Mumbai HQ",
        "buyer_gstin": "27AABCL1234K1Z8",
        "buyer_address": "L&T House, Ballard Estate",
        "buyer_city": "Mumbai",
        "buyer_state": "Maharashtra",
        "buyer_state_code": "27",
        "buyer_pincode": "400001",
        "buyer_phone": "9820012345",
        "buyer_email": "procurement@larsentoubro.com",
        "notes": "Fabricated steel structures for Mumbai Metro Line 6 — Batch 3",
        "terms": "Net 90 days. Stage-wise inspection. RA Bill basis.",
        "invoice_status": "issued",
        "items": [
            {"description": "Pre-Fab Steel Column (HEB 300)", "hsn_sac_code": "73089090", "quantity": 50, "unit": "TON", "unit_price": 85000, "gst_rate": 18},
            {"description": "Steel Roof Truss Assembly", "hsn_sac_code": "73089090", "quantity": 25, "unit": "SET", "unit_price": 120000, "gst_rate": 18},
            {"description": "Welded Plate Girder (12m)", "hsn_sac_code": "73089090", "quantity": 15, "unit": "PCS", "unit_price": 95000, "gst_rate": 18},
        ],
    }),
]


def _calc_item(item_data: dict, supply_type: str):
    qty = item_data["quantity"]
    price = item_data["unit_price"]
    taxable = qty * price
    gst_rate = item_data["gst_rate"]
    gst_amt = round(taxable * gst_rate / 100, 2)
    if supply_type == "intra_state":
        return {**item_data, "taxable_value": taxable, "cgst_amount": round(gst_amt / 2, 2), "sgst_amount": round(gst_amt / 2, 2), "igst_amount": 0, "cess_rate": 0, "cess_amount": 0, "discount_percent": 0, "discount_amount": 0, "total_amount": round(taxable + gst_amt, 2)}
    else:
        return {**item_data, "taxable_value": taxable, "cgst_amount": 0, "sgst_amount": 0, "igst_amount": gst_amt, "cess_rate": 0, "cess_amount": 0, "discount_percent": 0, "discount_amount": 0, "total_amount": round(taxable + gst_amt, 2)}


def _msme_class(turnover, assets):
    """Classify MSME based on Indian MSME Act 2020 criteria."""
    if turnover <= 5_00_00_000 and assets <= 1_00_00_000:
        return "Micro"
    elif turnover <= 50_00_00_000 and assets <= 10_00_00_000:
        return "Small"
    else:
        return "Medium"


def _generate_credit_scores(db: Session, vendors: list):
    """Generate comprehensive CreditScore records for each vendor."""
    grade_map = {
        (80, 101): "AAA", (70, 80): "AA", (60, 70): "A",
        (50, 60): "BBB", (40, 50): "BB", (30, 40): "B",
        (20, 30): "C", (0, 20): "D",
    }
    count = 0
    for vendor in vendors:
        cibil = vendor.cibil_score or 650
        cibil_comp = min(100, (cibil - 300) / 6)
        gst_comp = 85 if vendor.gst_compliance_status == "Regular" else 40
        repay_comp = random.uniform(65, 95)
        bank_comp = random.uniform(60, 90)
        inv_comp = random.uniform(55, 85)
        biz_comp = min(100, (2026 - vendor.year_of_establishment) * 6)
        total = round(cibil_comp * 0.25 + gst_comp * 0.20 + repay_comp * 0.15 + bank_comp * 0.15 + inv_comp * 0.10 + biz_comp * 0.15, 1)
        grade = "B"
        for (lo, hi), g in grade_map.items():
            if lo <= total < hi:
                grade = g
                break

        msme_cat = _msme_class(vendor.annual_turnover, vendor.business_assets_value)
        cs = CreditScore(
            vendor_id=vendor.id,
            total_score=total,
            risk_grade=grade,
            confidence_level=round(random.uniform(0.7, 0.95), 2),
            cibil_component=round(cibil_comp, 1),
            gst_compliance_component=round(gst_comp, 1),
            repayment_history_component=round(repay_comp, 1),
            bank_health_component=round(bank_comp, 1),
            invoice_quality_component=round(inv_comp, 1),
            business_stability_component=round(biz_comp, 1),
            recommended_interest_rate=round(max(8, 22 - total * 0.15), 1),
            recommended_max_funding=round(vendor.annual_turnover * (total / 100) * 0.8, 0),
            recommended_max_tenure_days=90 if total > 60 else 60,
            data_snapshot_json=json.dumps({
                "cibil_score": cibil, "turnover": vendor.annual_turnover,
                "gst_filings": vendor.total_gst_filings, "year_est": vendor.year_of_establishment,
                "msme_category": msme_cat, "udyam": vendor.udyam_registration_number,
                "employees": vendor.number_of_employees,
            }),
        )
        db.add(cs)
        count += 1
    return count


def _generate_verification_checks(db: Session, vendor):
    """Generate 7 realistic verification check records for a vendor."""
    msme_cat = _msme_class(vendor.annual_turnover, vendor.business_assets_value)
    checks = [
        {"check_type": "gstin", "status": "passed", "details": json.dumps({
            "result": "valid", "source": "sandbox_gst_api", "gstin": vendor.gstin,
            "legal_name": vendor.business_name.upper(), "status": "Active",
            "state": vendor.state, "api_response_time_ms": random.randint(800, 2000)
        })},
        {"check_type": "pan", "status": "passed", "details": json.dumps({
            "result": "valid", "source": "sandbox_pan_api", "pan": vendor.personal_pan,
            "name_on_pan": vendor.full_name.upper(),
            "pan_type": "Individual" if vendor.business_type == "Proprietorship" else "Company",
            "api_response_time_ms": random.randint(500, 1500)
        })},
        {"check_type": "aadhaar", "status": "passed", "details": json.dumps({
            "result": "format_valid", "source": "aadhaar_checksum",
            "aadhaar_last4": vendor.personal_aadhaar[-4:], "verhoeff_valid": True
        })},
        {"check_type": "cibil", "status": "passed", "details": json.dumps({
            "result": "good" if vendor.cibil_score >= 700 else "fair",
            "source": "invox_internal_scoring", "score": vendor.cibil_score,
            "grade": "Good" if vendor.cibil_score >= 700 else "Fair",
            "factors": ["Regular GST compliance", f"{vendor.total_gst_filings} filings", f"Est. {vendor.year_of_establishment}"]
        })},
        {"check_type": "bank", "status": "passed", "details": json.dumps({
            "result": "valid", "source": "sandbox_bank_api",
            "bank": vendor.bank_name, "ifsc_valid": True, "account_exists": True,
            "api_response_time_ms": random.randint(400, 1200)
        })},
        {"check_type": "udyam_msme", "status": "passed", "details": json.dumps({
            "result": "verified", "source": "udyam_registry",
            "udyam_number": vendor.udyam_registration_number,
            "msme_category": msme_cat,
            "enterprise_type": "Manufacturing" if "Manufacturing" in (vendor.business_category or "") or "Handloom" in (vendor.business_category or "") or "Food" in (vendor.business_category or "") or "Pharma" in (vendor.business_category or "") or "Steel" in (vendor.business_category or "") or "Auto" in (vendor.business_category or "") or "Ceramic" in (vendor.business_category or "") or "Leather" in (vendor.business_category or "") or "Garment" in (vendor.business_category or "") or "Electronics" in (vendor.business_category or "") else "Services",
            "date_of_registration": vendor.gst_registration_date,
            "api_response_time_ms": random.randint(600, 1800)
        })},
        {"check_type": "address", "status": "passed", "details": json.dumps({
            "result": "verified", "source": "gst_address_match",
            "gst_address": vendor.business_address, "confidence": round(random.uniform(0.88, 0.99), 2)
        })},
    ]
    for c in checks:
        vc = VerificationCheck(vendor_id=vendor.id, **c)
        db.add(vc)
    return len(checks)


# ══════════════════════════════════════════════════════════
#  MAIN SEED ENDPOINT
# ══════════════════════════════════════════════════════════

@router.post("/demo")
def seed_demo_data(db: Session = Depends(get_db)):
    """Seed database with 10 MSME vendors, 10 lenders, invoices, verification checks, credit scores, and marketplace listings."""

    if db.query(Vendor).count() > 0:
        return {"message": "Demo data already exists. Use /api/seed/reset first to clear.", "seeded": False}

    created = {"vendors": 0, "lenders": 0, "invoices": 0, "listings": 0, "checks": 0, "credit_scores": 0, "users": 0}

    # ── 1. MSME Vendors ──
    vendors = []
    for v_data in DEMO_VENDORS:
        vendor = Vendor(**v_data)
        db.add(vendor)
        db.flush()
        vendors.append(vendor)
        created["vendors"] += 1
        created["checks"] += _generate_verification_checks(db, vendor)

    # ── 2. Credit Scores ──
    created["credit_scores"] = _generate_credit_scores(db, vendors)

    # ── 3. MSME Lenders ──
    lenders = []
    for l_data in DEMO_LENDERS:
        lender = Lender(**l_data)
        db.add(lender)
        db.flush()
        lenders.append(lender)
        created["lenders"] += 1

    # ── 4. MSME Invoices + Marketplace Listings ──
    for vendor_idx, inv_data in DEMO_INVOICES:
        vendor = vendors[vendor_idx]
        items_raw = inv_data.pop("items")
        supply_type = inv_data["supply_type"]

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

        for idx, it in enumerate(processed_items, 1):
            item = InvoiceItem(invoice_id=invoice.id, item_number=idx, **it)
            db.add(item)

        block_hash = None
        try:
            block = add_block(db, "invoice", {
                "invoice_id": invoice.id,
                "invoice_number": invoice.invoice_number,
                "vendor_id": vendor.id,
                "grand_total": grand_total,
                "msme_category": _msme_class(vendor.annual_turnover, vendor.business_assets_value),
            })
            block_hash = block.block_hash
            invoice.blockchain_hash = block_hash
            invoice.block_index = block.block_index
        except Exception:
            pass

        requested_pct = 80
        requested_amt = round(grand_total * requested_pct / 100, 2)
        listing = MarketplaceListing(
            invoice_id=invoice.id,
            vendor_id=vendor.id,
            requested_percentage=requested_pct,
            requested_amount=requested_amt,
            discount_rate=round(10 + vendor_idx * 0.5, 1),
            max_interest_rate=round(12 + vendor_idx, 1),
            repayment_period_days=90,
            listing_status="open",
            risk_score=vendor.risk_score,
            blockchain_hash=block_hash,
        )
        db.add(listing)
        created["invoices"] += 1
        created["listings"] += 1

    db.commit()

    # ── 4b. Simulate FUNDED listings with repayment schedules (for vendors 1-4) ──
    funded_listings = db.query(MarketplaceListing).filter(
        MarketplaceListing.vendor_id.in_([v.id for v in vendors[:4]]),
        MarketplaceListing.listing_status == "open",
    ).all()

    now = datetime.now(timezone.utc)
    for idx, fl in enumerate(funded_listings):
        # Pick a lender to fund the listing
        funder_lender = lenders[idx % len(lenders)]
        funded_amt = fl.requested_amount
        interest_rate = fl.max_interest_rate

        # Update listing to "funded"
        fl.listing_status = "funded"
        fl.funded_amount = funded_amt
        fl.funded_by = funder_lender.name
        fl.lender_id = funder_lender.id
        fl.funded_at = now - timedelta(days=60 - idx * 10)
        fl.total_funded_amount = funded_amt
        fl.total_investors = 1

        # Create FractionalInvestment record
        fi = FractionalInvestment(
            listing_id=fl.id,
            lender_id=funder_lender.id,
            invested_amount=funded_amt,
            offered_interest_rate=interest_rate,
            ownership_percentage=100.0,
            expected_return=round(funded_amt * interest_rate / 100 * fl.repayment_period_days / 365, 2),
            status="active",
        )
        db.add(fi)

        # Create 3-installment repayment schedule
        total_with_interest = round(funded_amt * (1 + interest_rate / 100 * fl.repayment_period_days / 365), 2)
        per_installment = round(total_with_interest / 3, 2)
        principal_per = round(funded_amt / 3, 2)
        interest_per = round(per_installment - principal_per, 2)

        base_date = fl.funded_at
        for inst_num in range(1, 4):
            due = base_date + timedelta(days=30 * inst_num)
            # For vendor 1 (idx 0): installment 1 paid, 2 overdue, 3 pending
            # For vendor 2 (idx 1): installment 1 paid, 2 pending, 3 pending
            # For vendor 3 (idx 2): all pending (recently funded)
            # For vendor 4 (idx 3): installment 1 overdue, 2 pending, 3 pending
            if idx == 0 and inst_num == 1:
                status = "paid"
                paid_date = (due + timedelta(days=2)).strftime("%Y-%m-%d")
                paid_amount = per_installment
            elif idx == 0 and inst_num == 2:
                status = "overdue"
                paid_date = None
                paid_amount = None
            elif idx == 1 and inst_num == 1:
                status = "paid"
                paid_date = (due - timedelta(days=1)).strftime("%Y-%m-%d")
                paid_amount = per_installment
            elif idx == 3 and inst_num == 1:
                status = "overdue"
                paid_date = None
                paid_amount = None
            elif due.date() < now.date():
                status = "overdue"
                paid_date = None
                paid_amount = None
            else:
                status = "pending"
                paid_date = None
                paid_amount = None

            sched = RepaymentSchedule(
                listing_id=fl.id,
                installment_number=inst_num,
                due_date=due.strftime("%Y-%m-%d"),
                principal_amount=principal_per,
                interest_amount=interest_per,
                total_amount=per_installment,
                status=status,
                paid_date=paid_date,
                paid_amount=paid_amount,
            )
            db.add(sched)

        created["listings"] += 0  # already counted

    db.commit()

    # ── 5. Demo User Accounts ──
    for u_data in DEMO_USERS:
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
            vendor_id=vendors[u_data["vendor_idx"]].id if u_data.get("vendor_idx") is not None and u_data["vendor_idx"] < len(vendors) else None,
            lender_id=lenders[u_data["lender_idx"]].id if u_data.get("lender_idx") is not None and u_data["lender_idx"] < len(lenders) else None,
        )
        db.add(user)
        created["users"] += 1
    db.commit()

    # Build MSME summary
    msme_summary = []
    for v in vendors:
        cat = _msme_class(v.annual_turnover, v.business_assets_value)
        msme_summary.append({"name": v.business_name, "category": cat, "sector": v.business_category, "turnover": v.annual_turnover, "udyam": v.udyam_registration_number})

    return {
        "message": "MSME demo data seeded successfully!",
        "seeded": True,
        "created": created,
        "vendor_ids": [v.id for v in vendors],
        "lender_ids": [l.id for l in lenders],
        "msme_breakdown": msme_summary,
        "demo_logins": [
            {"role": f"Vendor {i+1} ({_msme_class(DEMO_VENDORS[i]['annual_turnover'], DEMO_VENDORS[i]['business_assets_value'])})", "email": f"vendor{i+1}@invox.demo", "password": DEMO_PASSWORD}
            for i in range(10)
        ] + [
            {"role": f"Lender {i+1}", "email": f"lender{i+1}@invox.demo", "password": DEMO_PASSWORD}
            for i in range(10)
        ] + [
            {"role": "Lender (alias)", "email": "lender@invox.demo", "password": DEMO_PASSWORD},
            {"role": "Admin", "email": "admin@invox.demo", "password": DEMO_PASSWORD},
        ],
        "hardcoded_registration_templates": [
            {"gstin": "09AABCT1332L1ZC", "pan": "AABCT1332L", "aadhaar": "876543210987", "company": "Tera Software Ltd (UP)"},
            {"gstin": "29AAACR5055K1Z3", "pan": "AAACR5055K", "aadhaar": "765432109876", "company": "Reliance Industries Ltd (KA)"},
            {"gstin": "06AAACR5055K1ZB", "pan": "AAACR5055K", "aadhaar": "654321098765", "company": "Reliance Industries Ltd (HR)"},
        ],
    }


@router.post("/demo-users")
def seed_demo_users(db: Session = Depends(get_db)):
    """Create demo login accounts linked to existing vendors/lenders."""
    vendors = db.query(Vendor).order_by(Vendor.id).all()
    lenders = db.query(Lender).order_by(Lender.id).all()

    if not vendors:
        return {"message": "No vendors found — run /api/seed/demo first", "created": 0}

    created = 0
    accounts = []
    for u_data in DEMO_USERS:
        existing = db.query(User).filter(User.email == u_data["email"]).first()
        if existing:
            accounts.append({"email": u_data["email"], "status": "already exists"})
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
        accounts.append({"email": u_data["email"], "status": "created"})

    db.commit()
    return {"message": f"Created {created} demo user accounts", "created": created, "accounts": accounts}


@router.post("/reset")
def reset_and_reseed(db: Session = Depends(get_db)):
    """Drop ALL data and re-seed from scratch."""
    from models import (
        ChatMessage, ChatConversation, NegotiationRound, NegotiationMessage,
        NegotiationSession, EMandateExecution, EMandateRegistration,
        FactoringAgreement, CreditScore, InvoiceVerificationReport,
        InvoiceRegistryEntry, Payment, FractionalInvestment,
        MarketplaceListing, InvoiceItem, Invoice, VerificationCheck,
        BlockchainBlock, Notification, ActivityLog, User, Lender, Vendor,
        RepaymentSchedule,
    )

    for model in [
        ChatMessage, ChatConversation,
        NegotiationRound, NegotiationMessage, NegotiationSession,
        EMandateExecution, EMandateRegistration, FactoringAgreement,
        CreditScore, InvoiceVerificationReport, InvoiceRegistryEntry,
        Payment, RepaymentSchedule, FractionalInvestment, MarketplaceListing,
        InvoiceItem, Invoice, VerificationCheck, BlockchainBlock,
        Notification, ActivityLog, User, Lender, Vendor,
    ]:
        try:
            db.query(model).delete()
        except Exception:
            db.rollback()
    db.commit()

    return seed_demo_data(db)

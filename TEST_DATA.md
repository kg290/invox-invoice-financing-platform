# InvoX — Sandbox.co.in Test Data
## 25 Verified Entities for Manual Testing

> **IMPORTANT**: Sandbox.co.in is a **live API gateway** — it connects to real Indian government databases (GST Network, NSDL, UIDAI). There are no "stored test users." All data below is **real, publicly available** company registration data pulled live from the GST Network via Sandbox API.

---

## ⚡ Quick Reference — How to Test InvoX

| Test Action | What You Need | API Status |
|---|---|---|
| **GST Verification** | Any GSTIN from tables below | ✅ Working |
| **PAN Verification** | Any PAN from tables below | ⚠️ Credits exhausted (needs recharge) |
| **Aadhaar e-KYC** | Real Aadhaar + OTP to holder's phone | ❌ Requires real person |
| **Bank Verification** | Real bank account + IFSC | ❌ Requires real account |
| **CIBIL Score** | PAN number | ✅ Internal scoring (no API needed) |
| **Login/Register** | Email + Phone + Password | ✅ Use `@invox.demo` for auto-OTP |

### Demo Login Credentials
- **Email**: any email ending with `@invox.demo` (e.g., `bilt@invox.demo`, `reliance@invox.demo`)
- **Password**: `Demo@1234`
- **OTP**: Auto-skipped for `@invox.demo` accounts

---

## 📊 25 Verified GSTINs (Live from GST Network)

### Company 1: BILT GRAPHIC PAPER PRODUCTS LIMITED
| # | GSTIN | PAN | State | City | Pincode | Status |
|---|---|---|---|---|---|---|
| 1 | `27AADCB2230M1ZT` | `AADCB2230M` | Maharashtra | Chandrapur | 442901 | Active |
| 2 | `07AADCB2230M1ZV` | `AADCB2230M` | Delhi | North Delhi | 110025 | Active |
| 3 | `33AADCB2230M1Z0` | `AADCB2230M` | Tamil Nadu | Chennai | 600017 | Active |
| 4 | `06AADCB2230M1ZX` | `AADCB2230M` | Haryana | Gurugram | 122002 | Active |
| 5 | `19AADCB2230M1ZQ` | `AADCB2230M` | West Bengal | Kolkata | 700020 | Active |

**Address (MH)**: PO Ballarpur Paper Mills, Paper Mills Compound, Allapalli Road, Ballarpur, Chandrapur, Maharashtra 442901  
**Address (DL)**: DTJ 1107 1108, DLF Tower B, Jasola, New Delhi 110025  
**Registered**: 01/07/2017 | **Type**: Public Limited Company

---

### Company 2: BHARTI AIRTEL LIMITED
| # | GSTIN | PAN | State | City | Pincode | Status |
|---|---|---|---|---|---|---|
| 6 | `27AAACB2894G1ZN` | `AAACB2894G` | Maharashtra | Mumbai | 400064 | Active |
| 7 | `29AAACB2894G1ZJ` | `AAACB2894G` | Karnataka | Bengaluru | 560029 | Active |
| 8 | `07AAACB2894G1ZP` | `AAACB2894G` | Delhi | New Delhi | 110020 | Active |
| 9 | `33AAACB2894G1ZU` | `AAACB2894G` | Tamil Nadu | Chennai | 600004 | Active |
| 10 | `06AAACB2894G1ZR` | `AAACB2894G` | Haryana | Gurugram | 122015 | Active |
| 11 | `36AAACB2894G1ZO` | `AAACB2894G` | Telangana | Hyderabad | 500016 | Active |
| 12 | `19AAACB2894G1ZK` | `AAACB2894G` | West Bengal | Kolkata | 700091 | Active |
| 13 | `09AAACB2894G1ZL` | `AAACB2894G` | Uttar Pradesh | Lucknow | 226010 | Active |

**Address (MH)**: 7th Floor, Interface 7, Malad Link Road, Malad West, Mumbai 400064  
**Address (KA)**: 55, Divyasree Towers, Bannerghatta Main Road, Bengaluru 560029  
**Address (DL)**: 224, Okhla Industrial Area, New Delhi 110020  
**Registered**: 01/07/2017 | **Type**: Public Limited Company

---

### Company 3: TERA SOFTWARE LIMITED
| # | GSTIN | PAN | State | City | Pincode | Status |
|---|---|---|---|---|---|---|
| 14 | `27AABCT1332L1ZE` | `AABCT1332L` | Maharashtra | Nagpur | 440001 | Active |
| 15 | `29AABCT1332L1ZA` | `AABCT1332L` | Karnataka | Bengaluru | 560004 | Active |
| 16 | `36AABCT1332L1ZF` | `AABCT1332L` | Telangana | Hyderabad | 500033 | Active |
| 17 | `19AABCT1332L1ZB` | `AABCT1332L` | West Bengal | Kolkata | 700064 | Active |
| 18 | `09AABCT1332L1ZC` | `AABCT1332L` | Uttar Pradesh | Agra | 282002 | Active |

**Address (MH)**: Block 8, Mangalwari Commercial Complex, Bazar Sadar, Kamptee Road, Nagpur 440001  
**Address (TS)**: 8-2-293/82/A/1107, Road No-55, Jubilee Hills, Hyderabad 500033  
**Registered**: 01/07/2017 | **Type**: Public Limited Company

---

### Company 4: RELIANCE INDUSTRIES LIMITED
| # | GSTIN | PAN | State | City | Pincode | Status |
|---|---|---|---|---|---|---|
| 19 | `27AAACR5055K1Z7` | `AAACR5055K` | Maharashtra | Thane (Navi Mumbai) | 400701 | Active |
| 20 | `29AAACR5055K1Z3` | `AAACR5055K` | Karnataka | Bengaluru | 560025 | Active |
| 21 | `07AAACR5055K1Z9` | `AAACR5055K` | Delhi | South Delhi | 110019 | Active |
| 22 | `33AAACR5055K1ZE` | `AAACR5055K` | Tamil Nadu | Chennai | 600004 | Active |
| 23 | `06AAACR5055K1ZB` | `AAACR5055K` | Haryana | Gurugram | 122003 | Active |
| 24 | `36AAACR5055K1Z8` | `AAACR5055K` | Telangana | Hyderabad | 500082 | Active |
| 25 | `19AAACR5055K1Z4` | `AAACR5055K` | West Bengal | Kolkata | 700091 | Active |

**Address (MH)**: 5, Reliance Corporate Park, Thane Belapur Road, Ghansoli, Navi Mumbai 400701  
**Address (DL)**: 10th Floor, International Trade Tower, Nehru Place, South Delhi 110019  
**Address (KA)**: 62/2, 2, Richmond, Bangalore 560025  
**Registered**: 01/07/2017 | **Type**: Public Limited Company

---

## 🔑 PAN Numbers (Extracted from GSTINs)

| # | PAN | Company Name | PAN Category | Entity Type |
|---|---|---|---|---|
| 1 | `AADCB2230M` | BILT GRAPHIC PAPER PRODUCTS LTD | Company | C (Company) |
| 2 | `AAACB2894G` | BHARTI AIRTEL LIMITED | Company | C (Company) |
| 3 | `AABCT1332L` | TERA SOFTWARE LIMITED | Company | C (Company) |
| 4 | `AAACR5055K` | RELIANCE INDUSTRIES LIMITED | Company | C (Company) |

> **Note**: PAN is embedded in GSTIN at characters 3-12. The 4th character of PAN indicates entity type:
> - `C` = Company, `P` = Person, `H` = HUF, `F` = Firm, `A` = AOP, `T` = Trust

---

## 🧪 Step-by-Step Testing Guide

### Test 1: Register a Vendor
```
1. Go to /register
2. Fill in:
   - Company: "BILT GRAPHIC PAPER PRODUCTS LIMITED"
   - Email: "bilt@invox.demo"
   - Phone: "9876543210"
   - PAN: "AADCB2230M"
   - GSTIN: "27AADCB2230M1ZT"
   - Password: "Demo@1234"
3. Submit → Should auto-skip OTP (demo account)
```

### Test 2: KYC Verification
```
1. Login as vendor
2. Go to KYC page
3. Enter PAN: "AADCB2230M"
4. Enter GSTIN: "27AADCB2230M1ZT"
5. Submit → GST verification will hit real GST Network
   - Should return: "BILT GRAPHIC PAPER PRODUCTS LIMITED", Active, Maharashtra
```

### Test 3: GST API Direct Test (via curl)
```bash
# Test GSTIN search
curl -X POST http://localhost:8000/api/govt/verify-gstin \
  -H "Content-Type: application/json" \
  -d '{"gstin": "27AAACR5055K1Z7"}'

# Expected: Reliance Industries Limited, Active, Maharashtra
```

### Test 4: Multiple Vendors (different states)
```
Register 5 vendors using different GSTINs:
1. bilt-mh@invox.demo     → 27AADCB2230M1ZT (BILT, Maharashtra)
2. airtel-ka@invox.demo   → 29AAACB2894G1ZJ (Airtel, Karnataka)
3. tera-ts@invox.demo     → 36AABCT1332L1ZF (Tera, Telangana)
4. reliance-dl@invox.demo → 07AAACR5055K1Z9 (Reliance, Delhi)
5. airtel-tn@invox.demo   → 33AAACB2894G1ZU (Airtel, Tamil Nadu)
```

---

## ⚠️ Limitations & What You CANNOT Test

| Feature | Why It Can't Be Tested | Workaround |
|---|---|---|
| **Aadhaar e-KYC** | Requires real Aadhaar + OTP to registered mobile | Use your own Aadhaar or skip |
| **PAN Verification** | Sandbox account PAN credits exhausted (403) | Recharge credits at sandbox.co.in dashboard |
| **Bank Account** | Requires real bank account + IFSC | Use your own bank details |
| **Individual PANs** | These are company PANs (4th char = C). For person PANs (4th char = P), you need a real individual's PAN | Use your own PAN for individual testing |

### How to Fix PAN Verification
1. Go to [Sandbox.co.in Dashboard](https://dashboard.sandbox.co.in)
2. Navigate to Credits/Billing
3. Add credits for "PAN Verification" API
4. Once recharged, PANs above will verify successfully

---

## 📋 Full Address Directory

| # | GSTIN | Full Address |
|---|---|---|
| 1 | 27AADCB2230M1ZT | PO Ballarpur Paper Mills, Allapalli Road, Chandrapur, MH 442901 |
| 2 | 07AADCB2230M1ZV | DTJ 1107, DLF Tower B, Jasola, New Delhi 110025 |
| 3 | 33AADCB2230M1Z0 | Old No 4 New No 7, VTB Centre, South Boag Road, T.Nagar, Chennai 600017 |
| 4 | 06AADCB2230M1ZX | Tower-C, First India Place, Mehrauli Gurugram Road, Gurugram 122002 |
| 5 | 19AADCB2230M1ZQ | 10 B, Macmet House, O C Ganguli Sarani, Lee Road, Kolkata 700020 |
| 6 | 27AAACB2894G1ZN | 7th Floor, Interface 7, Malad Link Road, Malad West, Mumbai 400064 |
| 7 | 29AAACB2894G1ZJ | 55, Divyasree Towers, Bannerghatta Main Road, Bengaluru 560029 |
| 8 | 07AAACB2894G1ZP | 224, Okhla Industrial Area, New Delhi 110020 |
| 9 | 33AAACB2894G1ZU | 42/147, Santhome High Road, Rosary Church Road, Mylapore, Chennai 600004 |
| 10 | 06AAACB2894G1ZR | Plot 16, Airtel Centre, Udyog Vihar Phase-IV, Gurugram 122015 |
| 11 | 36AAACB2894G1ZO | 1-8-437, Splendid Towers, HUDA Road, Begumpet, Hyderabad 500016 |
| 12 | 19AAACB2894G1ZK | Block EP-GP, Infinity Building, Salt Lake Sector V, Kolkata 700091 |
| 13 | 09AAACB2894G1ZL | TCG-77, Vibhuti Khand, Gomti Nagar, Lucknow 226010 |
| 14 | 27AABCT1332L1ZE | Block 8, Mangalwari Commercial Complex, Kamptee Road, Nagpur 440001 |
| 15 | 29AABCT1332L1ZA | D No-1/33, Flr II, Gollara Obalkappa Road, Bengaluru 560004 |
| 16 | 36AABCT1332L1ZF | 8-2-293/82/A/1107, Road No-55, Jubilee Hills, Hyderabad 500033 |
| 17 | 19AABCT1332L1ZB | AA/3, Salt Lake, Sector-1, Kolkata 700064 |
| 18 | 09AABCT1332L1ZC | 408, Narayan Towers, Sanjay Place, Agra 282002 |
| 19 | 27AAACR5055K1Z7 | 5, Reliance Corporate Park, Thane Belapur Road, Ghansoli, Navi Mumbai 400701 |
| 20 | 29AAACR5055K1Z3 | 62/2, 2, Richmond, Bangalore 560025 |
| 21 | 07AAACR5055K1Z9 | 10th Floor, International Trade Tower, Nehru Place, New Delhi 110019 |
| 22 | 33AAACR5055K1ZE | 89, A1 Towers, Dr Radhakrishnan Salai, Mylapore, Chennai 600004 |
| 23 | 06AAACR5055K1ZB | Reliance House, Unitech Commercial Tower-A, Netaji Subhash Marg, Gurugram 122003 |
| 24 | 36AAACR5055K1Z8 | 6-3-1090/B, Lake Shore Towers, Rajbhavan Road, Somajiguda, Hyderabad 500082 |
| 25 | 19AAACR5055K1Z4 | Plot 5, Godrej Waterside, Sector V, Salt Lake City, Kolkata 700091 |

---

*Generated on: $(date) via Sandbox.co.in GST Compliance API*  
*All GSTINs verified live against the Indian GST Network*

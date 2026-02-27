"""Full end-to-end registration test with verification."""
import requests
import json
import time

BASE = "http://localhost:8000"

print("=" * 60)
print("STEP 1: Register new vendor (Reliance TS)")
print("=" * 60)

r = requests.post(f"{BASE}/api/auth/register", json={
    "name": "Reliance Telangana",
    "email": "ril-ts@invox.demo",
    "phone": "9300000007",
    "password": "Demo@1234",
    "role": "vendor",
    "pan_number": "AAACR5055K",
    "aadhaar_number": "777788889999",
    "gstin": "36AAACR5055K1Z8",
})
print(f"  Status: {r.status_code}")
data = r.json()
print(f"  Response: {json.dumps(data, indent=2)[:500]}")

if r.status_code != 201:
    print("Registration failed!")
    exit(1)

otp = data.get("debug_otp", "")
user_id = data.get("user_id")
print(f"\n  OTP: {otp}")
print(f"  User ID: {user_id}")

print()
print("=" * 60)
print("STEP 2: Verify OTP (triggers auto vendor creation + Sandbox verification)")
print("=" * 60)

start = time.time()
r2 = requests.post(f"{BASE}/api/auth/verify-otp", json={
    "email": "ril-ts@invox.demo",
    "otp": str(otp),
}, timeout=120)
elapsed = time.time() - start
print(f"  Status: {r2.status_code} (took {elapsed:.1f}s)")

if r2.status_code != 200:
    print(f"  ERROR: {r2.text[:500]}")
    exit(1)

verify_data = r2.json()
user = verify_data.get("user", {})
print(f"  User: {user.get('name')} ({user.get('email')})")
print(f"  Role: {user.get('role')}")
print(f"  Vendor ID: {user.get('vendor_id')}")
print(f"  Verified: {user.get('is_verified')}")

token = verify_data.get("access_token", "")
if not user.get("vendor_id"):
    print("\n  WARNING: Vendor auto-creation failed! No vendor_id.")
    exit(1)

print()
print("=" * 60)
print("STEP 3: Fetch vendor profile to see verification checks")
print("=" * 60)

vendor_id = user["vendor_id"]
r3 = requests.get(f"{BASE}/api/vendors/{vendor_id}", headers={
    "Authorization": f"Bearer {token}"
})
print(f"  Status: {r3.status_code}")

if r3.status_code == 200:
    vendor = r3.json()
    print(f"  Business Name: {vendor.get('business_name')}")
    print(f"  GSTIN: {vendor.get('gstin')}")
    print(f"  PAN: {vendor.get('personal_pan')}")
    print(f"  State: {vendor.get('state')}")
    print(f"  Business Type: {vendor.get('business_type')}")
    print(f"  Year of Establishment: {vendor.get('year_of_establishment')}")
    print(f"  CIBIL Score: {vendor.get('cibil_score')}")
    print(f"  Risk Score: {vendor.get('risk_score')}")
    print(f"  Profile Status: {vendor.get('profile_status')}")
    print(f"  GST Compliance: {vendor.get('gst_compliance_status')}")
    print(f"  Address: {vendor.get('address', '')[:80]}")
    
    checks = vendor.get("verification_checks", [])
    print(f"\n  Verification Checks: {len(checks)}")
    for c in checks:
        details = {}
        try:
            details = json.loads(c.get("details", "{}"))
        except:
            pass
        status = c.get("status", details.get("status", "?"))
        check_type = c.get("check_type", details.get("check", "?"))
        message = details.get("message", "")[:80]
        icon = "pass" if status == "passed" else ("WARN" if status == "warning" else "FAIL")
        print(f"    [{icon}] {check_type}: {message}")

print()
print("ALL DONE!")

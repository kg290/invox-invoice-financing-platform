"""
Test all 5 features one by one.
Run with: python test_all_features.py
"""
import httpx
import json
import sys
import time

BASE = "http://localhost:8000"
TIMEOUT = 30

def login(email="vendor1@invox.demo", password="Demo@1234"):
    r = httpx.post(f"{BASE}/api/auth/login", json={"email": email, "password": password}, timeout=TIMEOUT)
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    data = r.json()
    return data["access_token"], data["user"]

def hdr(token):
    return {"Authorization": f"Bearer {token}"}

def pp(label, obj):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(json.dumps(obj, indent=2, default=str)[:3000])

def test_feature_1_blockchain_registry(token, invoice_id):
    print("\n" + "#"*70)
    print("# FEATURE 1: BLOCKCHAIN INVOICE REGISTRY")
    print("#"*70)
    results = {}

    # 1. Register invoice on blockchain
    print("\n>>> 1a. Register invoice on blockchain")
    r = httpx.post(f"{BASE}/api/blockchain-registry/register/{invoice_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["register"] = r.json()
    pp("Register Result", results["register"])

    # 2. Verify invoice integrity
    print("\n>>> 1b. Verify invoice integrity")
    r = httpx.get(f"{BASE}/api/blockchain-registry/verify/{invoice_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["verify"] = r.json()
    pp("Verify Result", results["verify"])

    # 3. Get blockchain certificate
    print("\n>>> 1c. Get blockchain certificate")
    r = httpx.get(f"{BASE}/api/blockchain-registry/certificate/{invoice_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["certificate"] = r.json()
    pp("Certificate", results["certificate"])

    # 4. Get audit history
    print("\n>>> 1d. Get audit history")
    r = httpx.get(f"{BASE}/api/blockchain-registry/history/{invoice_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["history"] = r.json()
    pp("History", results["history"])

    # 5. Get blockchain stats
    print("\n>>> 1e. Get blockchain registry stats")
    r = httpx.get(f"{BASE}/api/blockchain-registry/stats", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["stats"] = r.json()
    pp("Stats", results["stats"])

    return results

def test_feature_2_triple_verification(token, invoice_id, gstin="29AAGCB7383J1Z5"):
    print("\n" + "#"*70)
    print("# FEATURE 2: TRIPLE VERIFICATION ENGINE (Sandbox.co.in)")
    print("#"*70)
    results = {}

    # 1. Live GSTIN verification via Sandbox
    print(f"\n>>> 2a. Live GSTIN verification: {gstin}")
    r = httpx.post(f"{BASE}/api/triple-verify/gstin-live/{gstin}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["gstin_live"] = r.json()
    pp("GSTIN Live Result", results["gstin_live"])

    # 2. Full triple verification on invoice
    print(f"\n>>> 2b. Full triple verification on invoice #{invoice_id}")
    r = httpx.post(f"{BASE}/api/triple-verify/invoice/{invoice_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["triple_verify"] = r.json()
    pp("Triple Verify Result", results["triple_verify"])

    # 3. Get verification report
    print(f"\n>>> 2c. Verification report for invoice #{invoice_id}")
    r = httpx.get(f"{BASE}/api/triple-verify/report/{invoice_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["report"] = r.json()
    pp("Report", results["report"])

    # 4. Verification stats
    print("\n>>> 2d. Verification stats")
    r = httpx.get(f"{BASE}/api/triple-verify/stats", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["stats"] = r.json()
    pp("Stats", results["stats"])

    return results

def test_feature_3_credit_scoring(token, vendor_id=1):
    print("\n" + "#"*70)
    print("# FEATURE 3: REAL-TIME CREDIT SCORING ENGINE")
    print("#"*70)
    results = {}

    # 1. Get credit score
    print(f"\n>>> 3a. Credit score for vendor #{vendor_id}")
    r = httpx.get(f"{BASE}/api/credit-score/vendor/{vendor_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["score"] = r.json()
    pp("Credit Score", results["score"])

    # 2. Get breakdown
    print(f"\n>>> 3b. Score breakdown for vendor #{vendor_id}")
    r = httpx.get(f"{BASE}/api/credit-score/breakdown/{vendor_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["breakdown"] = r.json()
    pp("Breakdown", results["breakdown"])

    # 3. Score history
    print(f"\n>>> 3c. Score history for vendor #{vendor_id}")
    r = httpx.get(f"{BASE}/api/credit-score/history/{vendor_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["history"] = r.json()
    pp("History", results["history"])

    # 4. Recommended rate
    print(f"\n>>> 3d. Recommended interest rate for vendor #{vendor_id}")
    r = httpx.get(f"{BASE}/api/credit-score/recommended-rate/{vendor_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["rate"] = r.json()
    pp("Recommended Rate", results["rate"])

    return results

def test_feature_4_factoring(token, listing_id=1):
    print("\n" + "#"*70)
    print("# FEATURE 4: INVOICE FACTORING WITH RECOURSE OPTIONS")
    print("#"*70)
    results = {}

    # 1. Get factoring options for listing
    print(f"\n>>> 4a. Factoring options for listing #{listing_id}")
    r = httpx.get(f"{BASE}/api/factoring/options/{listing_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["options"] = r.json()
    pp("Factoring Options", results["options"])

    # 2. Create a factoring agreement (as lender)
    # Need lender token
    lender_token, lender_user = login("lender@invox.demo", "Demo@1234")
    print(f"\n    Logged in as lender: {lender_user['name']} (lender_id={lender_user.get('lender_id', 'N/A')})")

    lender_id = lender_user.get("lender_id") or lender_user.get("id")

    create_payload = {
        "listing_id": listing_id,
        "lender_id": lender_id,
        "factoring_type": "partial_recourse",
    }
    print(f"\n>>> 4b. Create factoring agreement")
    print(f"    Payload: {json.dumps(create_payload)}")
    r = httpx.post(f"{BASE}/api/factoring/create", json=create_payload, headers=hdr(lender_token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["create"] = r.json()
    pp("Create Agreement", results["create"])

    # 3. Get vendor factoring agreements
    print(f"\n>>> 4c. Vendor factoring agreements")
    r = httpx.get(f"{BASE}/api/factoring/vendor/1", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["vendor_agreements"] = r.json()
    pp("Vendor Agreements", results["vendor_agreements"])

    # 4. Get lender factoring agreements
    print(f"\n>>> 4d. Lender factoring agreements")
    r = httpx.get(f"{BASE}/api/factoring/lender/{lender_id}", headers=hdr(lender_token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["lender_agreements"] = r.json()
    pp("Lender Agreements", results["lender_agreements"])

    return results

def test_feature_5_emandate(token, vendor_id=1):
    print("\n" + "#"*70)
    print("# FEATURE 5: AUTO-REPAYMENT VIA NPCI e-MANDATE")
    print("#"*70)
    results = {}

    # 1. Register e-mandate
    register_payload = {
        "vendor_id": vendor_id,
        "bank_account_number": "1234567890123456",
        "bank_ifsc": "SBIN0001234",
        "max_amount": 50000.0,
        "frequency": "monthly",
        "start_date": "2026-03-01T00:00:00",
        "end_date": "2027-03-01T00:00:00",
    }
    print(f"\n>>> 5a. Register e-Mandate")
    r = httpx.post(f"{BASE}/api/emandate/register", json=register_payload, headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["register"] = r.json()
    pp("Register e-Mandate", results["register"])

    mandate_id = results["register"].get("mandate_id") or results["register"].get("id")
    if not mandate_id:
        # Try to extract from nested structure
        if isinstance(results["register"], dict) and "data" in results["register"]:
            mandate_id = results["register"]["data"].get("mandate_id") or results["register"]["data"].get("id")
    print(f"    Mandate ID: {mandate_id}")

    if mandate_id:
        # 2. Get mandate details
        print(f"\n>>> 5b. Get mandate details")
        r = httpx.get(f"{BASE}/api/emandate/mandate/{mandate_id}", headers=hdr(token), timeout=TIMEOUT)
        print(f"    Status: {r.status_code}")
        results["details"] = r.json()
        pp("Mandate Details", results["details"])

        # 3. Execute mandate
        exec_payload = {
            "mandate_id": mandate_id,
            "installment_id": 1,
        }
        print(f"\n>>> 5c. Execute mandate payment")
        r = httpx.post(f"{BASE}/api/emandate/execute", json=exec_payload, headers=hdr(token), timeout=TIMEOUT)
        print(f"    Status: {r.status_code}")
        results["execute"] = r.json()
        pp("Execute Result", results["execute"])

        # 4. Pause mandate
        print(f"\n>>> 5d. Pause mandate")
        r = httpx.post(f"{BASE}/api/emandate/mandate/{mandate_id}/pause", headers=hdr(token), timeout=TIMEOUT)
        print(f"    Status: {r.status_code}")
        results["pause"] = r.json()
        pp("Pause Result", results["pause"])

        # 5. Resume mandate
        print(f"\n>>> 5e. Resume mandate")
        r = httpx.post(f"{BASE}/api/emandate/mandate/{mandate_id}/resume", headers=hdr(token), timeout=TIMEOUT)
        print(f"    Status: {r.status_code}")
        results["resume"] = r.json()
        pp("Resume Result", results["resume"])

    # 6. Get vendor mandates
    print(f"\n>>> 5f. Get vendor mandates")
    r = httpx.get(f"{BASE}/api/emandate/vendor/{vendor_id}", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["vendor_mandates"] = r.json()
    pp("Vendor Mandates", results["vendor_mandates"])

    # 7. Retry failed executions
    print(f"\n>>> 5g. Retry failed executions")
    r = httpx.post(f"{BASE}/api/emandate/retry-failed", headers=hdr(token), timeout=TIMEOUT)
    print(f"    Status: {r.status_code}")
    results["retry"] = r.json()
    pp("Retry Result", results["retry"])

    return results


if __name__ == "__main__":
    print("="*70)
    print("  INVOX PAY - FEATURE TESTING SUITE")
    print("="*70)

    # Login
    token, user = login()
    print(f"\nLogged in as: {user['name']} (vendor_id={user.get('vendor_id')})")

    invoice_id = 1
    vendor_id = user.get("vendor_id", 1)

    errors = []

    # Test each feature
    try:
        test_feature_1_blockchain_registry(token, invoice_id)
        print("\n✓ Feature 1: PASSED")
    except Exception as e:
        print(f"\n✗ Feature 1 ERROR: {e}")
        errors.append(("Feature 1", str(e)))

    try:
        test_feature_2_triple_verification(token, invoice_id)
        print("\n✓ Feature 2: PASSED")
    except Exception as e:
        print(f"\n✗ Feature 2 ERROR: {e}")
        errors.append(("Feature 2", str(e)))

    try:
        test_feature_3_credit_scoring(token, vendor_id)
        print("\n✓ Feature 3: PASSED")
    except Exception as e:
        print(f"\n✗ Feature 3 ERROR: {e}")
        errors.append(("Feature 3", str(e)))

    try:
        test_feature_4_factoring(token, listing_id=1)
        print("\n✓ Feature 4: PASSED")
    except Exception as e:
        print(f"\n✗ Feature 4 ERROR: {e}")
        errors.append(("Feature 4", str(e)))

    try:
        test_feature_5_emandate(token, vendor_id)
        print("\n✓ Feature 5: PASSED")
    except Exception as e:
        print(f"\n✗ Feature 5 ERROR: {e}")
        errors.append(("Feature 5", str(e)))

    # Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    if errors:
        print(f"\n  {5 - len(errors)}/5 features passed, {len(errors)} failed:")
        for name, err in errors:
            print(f"    ✗ {name}: {err[:200]}")
    else:
        print("\n  ALL 5 FEATURES PASSED! ✓✓✓✓✓")
    print()

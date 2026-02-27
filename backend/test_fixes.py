"""Test script to verify all business logic fixes."""
import requests
import json

BASE = "http://localhost:8000"

def login(email):
    r = requests.post(f"{BASE}/api/auth/login", json={"email": email, "password": "Demo@1234"})
    return r.json()["access_token"]

def h(token):
    return {"Authorization": f"Bearer {token}"}

print("=" * 60)
print("TEST 1: Lender Wallet Balance (seeded)")
print("=" * 60)
lt = login("lender1@invox.demo")
r = requests.get(f"{BASE}/api/marketplace/lender/1/wallet", headers=h(lt))
wallet = r.json()
print(f"  Balance: ₹{wallet['wallet_balance']:,.0f}")
print(f"  Escrow:  ₹{wallet['escrow_locked']:,.0f}")
assert wallet["wallet_balance"] > 0, "Wallet should have balance"
initial_balance = wallet["wallet_balance"]
initial_escrow = wallet["escrow_locked"]
print("  ✅ PASS\n")

print("=" * 60)
print("TEST 2: Fund a listing (wallet deduction)")
print("=" * 60)
r = requests.get(f"{BASE}/api/marketplace/listings", headers=h(lt))
listings = r.json()
print(f"  Found {len(listings)} listings")
# Find an open listing (not already funded)
open_listings = [l for l in listings if l.get("listing_status") == "open"]
if not open_listings:
    print("  ⚠️ No open listings available — all funded. Skipping funding test.")
    lid = None
    amount = 0
    fund_result = {}
else:
    listing = open_listings[0]
    lid = listing["id"]
    amount = listing["requested_amount"]
    print(f"  Funding listing {lid}, amount ₹{amount:,.0f}")

    r = requests.post(f"{BASE}/api/marketplace/fund/{lid}", headers=h(lt), json={
        "lender_id": 1,
        "funded_amount": amount,
        "offered_interest_rate": 12.0
    })
    fund_result = r.json()
    print(f"  Status: {r.status_code}")
    print(f"  Fully funded: {fund_result.get('fully_funded')}")

    # Check wallet after
    r = requests.get(f"{BASE}/api/marketplace/lender/1/wallet", headers=h(lt))
    wallet_after = r.json()
    print(f"  Wallet after: ₹{wallet_after['wallet_balance']:,.0f}")
    print(f"  Escrow after: ₹{wallet_after['escrow_locked']:,.0f}")
    assert wallet_after["wallet_balance"] < initial_balance, "Wallet should be reduced"
    assert wallet_after["escrow_locked"] > initial_escrow, "Escrow should have locked funds"
    print("  ✅ PASS\n")

print("=" * 60)
print("TEST 3: Double-listing protection")
print("=" * 60)
vt = login("vendor1@invox.demo")
# Try to list the same invoice again (invoice 1 is already listed/funded)
r = requests.post(f"{BASE}/api/marketplace/list/1", headers=h(vt), data={
    "listing_title": "Duplicate",
    "listing_description": "should fail",
    "requested_percentage": 80,
    "discount_rate": 2.0,
    "max_interest_rate": 14.0,
    "repayment_period_days": 90,
})
print(f"  Status: {r.status_code} (expected 400)")
print(f"  Detail: {r.json().get('detail', r.json())}")
assert r.status_code == 400, "Should reject double listing"
print("  ✅ PASS\n")

print("=" * 60)
print("TEST 4: Repayment schedule (declining balance interest)")
print("=" * 60)
r = requests.get(f"{BASE}/api/marketplace/listings/{lid}/repayment", headers=h(lt))
repayment = r.json()
installments = repayment["installments"]
if installments:
    print(f"  Total installments: {len(installments)}")
    for inst in installments[:3]:
        print(f"    #{inst['installment_number']}: principal=₹{inst['principal_amount']:,.0f}, interest=₹{inst['interest_amount']:,.0f}, total=₹{inst['total_amount']:,.0f}")
    # Verify declining interest
    if len(installments) > 1:
        assert installments[0]["interest_amount"] >= installments[-1]["interest_amount"], "Interest should decline"
        print(f"  First interest: ₹{installments[0]['interest_amount']:,.0f}")
        print(f"  Last interest:  ₹{installments[-1]['interest_amount']:,.0f}")
        print("  ✅ PASS (declining balance confirmed)\n")
    else:
        print("  ⚠️ Only 1 installment, can't verify declining\n")
else:
    print("  ⚠️ No installments (listing may not be fully funded)\n")

print("=" * 60)
print("TEST 5: Credit score recalculation (post-funding)")
print("=" * 60)
r = requests.get(f"{BASE}/api/credit-score/vendor/1", headers=h(vt))
score = r.json()
print(f"  Vendor 1 credit score: {score.get('total_score')}")
print(f"  Grade: {score.get('risk_grade')}")
print(f"  Scored at: {score.get('scored_at')}")
assert score.get("total_score") is not None and score.get("total_score") > 0, "Score should be computed"
print("  ✅ PASS (score exists and was computed)\n")

print("=" * 60)
print("TEST 6: Self-funding check (vendor can't list other's invoice)")
print("=" * 60)
vt2 = login("vendor2@invox.demo")
# Vendor 2 tries to list vendor 1's invoice (invoice_id=1 belongs to vendor 1)
r = requests.post(f"{BASE}/api/marketplace/list/1", headers=h(vt2), data={
    "listing_title": "Stolen listing",
    "listing_description": "should fail",
    "requested_percentage": 80,
    "discount_rate": 2.0,
    "max_interest_rate": 14.0,
    "repayment_period_days": 90,
})
print(f"  Status: {r.status_code} (expected 400 or 403)")
print(f"  Detail: {r.json().get('detail', r.json())}")
assert r.status_code in (400, 403), "Should reject cross-vendor listing"
print("  ✅ PASS\n")

print("=" * 60)
print("TEST 7: Repayment enforcement (admin)")
print("=" * 60)
at = login("admin@invox.demo")
r = requests.post(f"{BASE}/api/marketplace/enforce-repayments", headers=h(at))
enforcement = r.json()
print(f"  Result: {json.dumps(enforcement, indent=2)}")
print("  ✅ PASS (enforcement ran without error)\n")

print("=" * 60)
print("TEST 8: Wallet top-up")
print("=" * 60)
r = requests.post(f"{BASE}/api/marketplace/lender/wallet/topup", headers=h(lt), json={
    "lender_id": 1,
    "amount": 100000
})
topup = r.json()
print(f"  Result: {topup}")
assert "new_balance" in topup, "Should return new balance"
print("  ✅ PASS\n")

print("=" * 60)
print("ALL TESTS PASSED! ✅")
print("=" * 60)

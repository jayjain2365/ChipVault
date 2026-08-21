"""
PUF-Pay — Critical Security & Edge Case Test Suite
Tests attack vectors, boundary conditions, and pipeline integrity
GIFT IFIH Young Builders Program 2026
"""
import sys, os, json, hashlib, copy
from datetime import datetime, date, timedelta

sys.stdout.reconfigure(encoding="utf-8")
sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))

from agent3_puf_auth   import sign_transaction, verify_transaction
from agent2_compliance import check_compliance
from agent1_parser     import parse_document

SEP  = "-" * 64
PASS_COUNT = 0
FAIL_COUNT = 0

with open("synthetic_docs.json") as f:
    docs = json.load(f)

ENROLLED_PUBKEY = sign_transaction("ENROLLMENT", chip="A")["public_key"]

def header(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def check(label, condition, detail=""):
    global PASS_COUNT, FAIL_COUNT
    icon = "[PASS]" if condition else "[FAIL]"
    print(f"{icon}  {label}")
    if detail:
        print(f"        {detail}")
    if condition:
        PASS_COUNT += 1
    else:
        FAIL_COUNT += 1
    return condition

# Replicate TX builder (same logic as app.py)
def build_tx(swift, note="TEST"):
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    dochash = hashlib.sha256(
        json.dumps(swift, sort_keys=True).encode()
    ).hexdigest()[:16].upper()
    return (
        f"APPROVE|LC:{swift['doc_id']}"
        f"|USD:{swift['amount_usd']}"
        f"|DOCHASH:{dochash}"
        f"|TS:{ts}"
        f"|NOTE:{note}"
    )

# Inline compliance rule logic (mirrors agent2_compliance.py rules)
def evaluate_rules(swift, bl):
    issues = []
    if swift["expiry_date"] < swift["issue_date"]:
        issues.append("CRITICAL")
    if not bl["goods_match"]:
        issues.append("CRITICAL")
    if swift["amount_usd"] > 200000:
        issues.append("FLAG")
    if swift["port_of_loading"] != bl["port_of_loading"]:
        issues.append("CRITICAL")
    status = ("REJECTED" if any(i == "CRITICAL" for i in issues)
              else "FLAGGED" if issues else "CLEARED")
    return status

# ─────────────────────────────────────────────────────────
# SECTION A — Cryptographic Attacks (no AWS required)
# ─────────────────────────────────────────────────────────
header("SECTION A — Cryptographic Attack Resistance")

swift0 = docs[0]["swift"]

# A1: Sign a document. Tamper with the amount. Signature must fail.
tx_orig   = build_tx(swift0, note="ORIG")
auth_orig = sign_transaction(tx_orig, chip="A")
tampered  = copy.deepcopy(swift0)
tampered["amount_usd"] = 999_999_999
tx_tampered = build_tx(tampered, note="ORIG")   # same note, different DOCHASH
ok = not verify_transaction(tx_tampered, auth_orig["signature"], ENROLLED_PUBKEY)
check("A1  Document tamper — signature invalidated by DOCHASH",
      ok, f"tampered amount {tampered['amount_usd']:,} vs original {swift0['amount_usd']:,}")

# A2: Sign LC-1. Try to authorise LC-2 with LC-1's signature.
tx_lc1  = build_tx(docs[0]["swift"], note="A")
tx_lc2  = build_tx(docs[1]["swift"], note="A")
auth_a1 = sign_transaction(tx_lc1, chip="A")
ok = not verify_transaction(tx_lc2, auth_a1["signature"], ENROLLED_PUBKEY)
check("A2  Cross-document attack — LC-1 signature cannot authorise LC-2", ok,
      "Different DOCHASH → different TX string → signature mismatch")

# A3: Bit-flip one byte in the signature — must reject.
sig    = auth_orig["signature"]
flipped_byte = format(int(sig[:2], 16) ^ 0xFF, "02x")
bad_sig = flipped_byte + sig[2:]
ok = not verify_transaction(tx_orig, bad_sig, ENROLLED_PUBKEY)
check("A3  Bit-flip attack on signature — rejected", ok,
      f"Original sig[:2]={sig[:2]}  Flipped={flipped_byte}")

# A4: Timestamp replay — two TX strings at different times, same doc.
#     The sigs are bound to different strings; cannot cross-use.
import time as _time
tx_t1 = build_tx(swift0, note="PAY")
_time.sleep(1)
tx_t2 = build_tx(swift0, note="PAY")
auth_t1 = sign_transaction(tx_t1, chip="A")
ok = (tx_t1 != tx_t2)  # different timestamps embedded
cross = verify_transaction(tx_t2, auth_t1["signature"], ENROLLED_PUBKEY)
check("A4  Timestamp prevents reuse — two TX strings differ", ok,
      f"TS in tx_t1 != TS in tx_t2 → cannot reuse same signature")
check("A4b Replaying tx_t1 sig against tx_t2 fails verification", not cross,
      f"cross-verify result: {cross} (expected False)")

# A5: Chip B NEVER passes verification — across 5 different documents.
all_blocked = True
for i in range(5):
    sw  = docs[i]["swift"]
    tx  = build_tx(sw, note="ATTACK")
    ab  = sign_transaction(tx, chip="B")
    if verify_transaction(tx, ab["signature"], ENROLLED_PUBKEY):
        all_blocked = False
check("A5  Chip B NEVER approved across 5 different documents", all_blocked,
      "All 5 Chip B signatures rejected against Chip A enrolled key")

# A6: Chip A ALWAYS passes verification — across 5 different documents.
all_approved = True
for i in range(5):
    sw  = docs[i]["swift"]
    tx  = build_tx(sw, note="LEGIT")
    aa  = sign_transaction(tx, chip="A")
    if not verify_transaction(tx, aa["signature"], ENROLLED_PUBKEY):
        all_approved = False
check("A6  Chip A ALWAYS approved across 5 different documents", all_approved,
      "All 5 Chip A signatures verified against enrolled key")

# A7: Chip B key cannot impersonate Chip A even with Chip B's OWN public key.
tx_b   = build_tx(swift0, note="SPOOF")
auth_b = sign_transaction(tx_b, chip="B")
# Chip B signs, bank checks against ENROLLED_PUBKEY (Chip A) — must fail
ok_enrolled = not verify_transaction(tx_b, auth_b["signature"], ENROLLED_PUBKEY)
# Chip B sig DOES verify against Chip B's own key (cryptographically valid)
ok_own = verify_transaction(tx_b, auth_b["signature"], auth_b["public_key"])
check("A7  Chip B self-consistent but bank rejects it",
      ok_enrolled and ok_own,
      f"vs enrolled key: {not ok_enrolled}  vs own key: {ok_own}  — only enrolled key is what matters")

# A8: Empty / whitespace transaction string — crypto must still work.
tx_empty = "   "
try:
    ae = sign_transaction(tx_empty, chip="A")
    ve = verify_transaction(tx_empty, ae["signature"], ENROLLED_PUBKEY)
    check("A8  Empty TX string — signs and verifies (no crash)", ve,
          "Edge case: even whitespace-only strings are handled")
except Exception as ex:
    check("A8  Empty TX string — no crash", False, str(ex)[:120])

# ─────────────────────────────────────────────────────────
# SECTION B — Compliance Rule Edge Cases (requires AWS)
# ─────────────────────────────────────────────────────────
header("SECTION B — Compliance Rule Edge Cases (inline rule check, no AWS)")

today      = date.today().isoformat()
future     = (date.today() + timedelta(days=60)).isoformat()
yesterday  = (date.today() - timedelta(days=1)).isoformat()

base_swift = {
    "doc_type": "SWIFT_MT700",
    "doc_id": "TEST001",
    "issue_date": today,
    "expiry_date": future,
    "applicant": "Test Co",
    "beneficiary": "Test Exports",
    "issuing_bank": "Test Bank",
    "amount_usd": 100000,
    "currency": "USD",
    "goods_description": "Electronic Components",
    "port_of_loading": "Mundra",
    "port_of_discharge": "Singapore",
    "anomaly_injected": False,
    "anomaly_type": "none",
    "compliance_note": "OK",
}
base_bl = {
    "doc_type": "BILL_OF_LADING",
    "bl_number": "BL-TEST",
    "linked_lc": "TEST001",
    "port_of_loading": "Mundra",
    "port_of_discharge": "Singapore",
    "goods": "Electronic Components",
    "goods_match": True,
    "gross_weight_kg": 1000,
    "containers": 2,
    "bl_date": today,
}

# B1: Amount exactly $200,000 — should be CLEARED (rule is >, not >=)
s = copy.deepcopy(base_swift); s["amount_usd"] = 200000
st = evaluate_rules(s, base_bl)
check("B1  Amount exactly $200,000 → CLEARED  (rule: > not >=)", st == "CLEARED",
      f"status={st}")

# B2: Amount $200,000.01 — should be FLAGGED
s = copy.deepcopy(base_swift); s["amount_usd"] = 200000.01
st = evaluate_rules(s, base_bl)
check("B2  Amount $200,000.01 → FLAGGED", st == "FLAGGED", f"status={st}")

# B3: Expiry == issue date — CLEARED (rule is <, not <=; same-day LC is unusual but passes)
s = copy.deepcopy(base_swift); s["expiry_date"] = today; s["issue_date"] = today
st = evaluate_rules(s, base_bl)
check("B3  Expiry == issue date → CLEARED  (boundary — rule uses strict <)",
      st == "CLEARED",
      f"status={st}  NOTE: same-day expiry is questionable; consider tightening to <=")

# B4: Expiry one day BEFORE issue — REJECTED
s = copy.deepcopy(base_swift); s["expiry_date"] = yesterday; s["issue_date"] = today
st = evaluate_rules(s, base_bl)
check("B4  Expiry one day before issue → REJECTED", st == "REJECTED", f"status={st}")

# B5: Multiple CRITICAL issues — still REJECTED (not FLAGGED)
s  = copy.deepcopy(base_swift)
s["amount_usd"]   = 500000         # FLAG
s["expiry_date"]  = yesterday      # CRITICAL
bl = copy.deepcopy(base_bl)
bl["goods_match"] = False          # CRITICAL
bl["port_of_loading"] = "Chennai"  # CRITICAL
st = evaluate_rules(s, bl)
check("B5  3 CRITICAL + 1 FLAG simultaneously → REJECTED  (not FLAGGED)", st == "REJECTED",
      f"status={st}  (CRITICAL takes priority over FLAG)")

# B6: FLAG-only doc (high amount, no other issues) → FLAGGED
s = copy.deepcopy(base_swift); s["amount_usd"] = 1_000_000
st = evaluate_rules(s, base_bl)
check("B6  Flag-only (amount $1M, no anomalies) → FLAGGED", st == "FLAGGED",
      f"status={st}")

# B7: REJECTED doc with high amount — status must be REJECTED not FLAGGED
s  = copy.deepcopy(base_swift)
s["amount_usd"]  = 500000          # FLAG — but…
s["expiry_date"] = yesterday       # CRITICAL overrides
st = evaluate_rules(s, base_bl)
check("B7  CRITICAL + FLAG combined → REJECTED  (CRITICAL wins)", st == "REJECTED",
      f"status={st}")

# B8: Goods mismatch — REJECTED regardless of amount
s  = copy.deepcopy(base_swift); s["amount_usd"] = 50000
bl = copy.deepcopy(base_bl);  bl["goods_match"] = False
st = evaluate_rules(s, bl)
check("B8  Goods mismatch → REJECTED  (low amount does not save it)", st == "REJECTED",
      f"status={st}")

# ─────────────────────────────────────────────────────────
# SECTION C — Pipeline Integrity (requires AWS Bedrock)
# ─────────────────────────────────────────────────────────
header("SECTION C — End-to-End Pipeline Integrity (AWS Bedrock)")

# C1: First CLEARED doc — full pipeline → APPROVED with Chip A
cleared_doc = next(
    d for d in docs
    if not d["swift"]["anomaly_injected"] and d["swift"]["amount_usd"] <= 200000
)
try:
    parsed  = parse_document(cleared_doc["swift"])
    result  = check_compliance(cleared_doc["swift"], cleared_doc["bill_of_lading"], parsed)
    tx      = build_tx(cleared_doc["swift"], note="PIPELINE-TEST")
    auth_ca = sign_transaction(tx, chip="A")
    ok_a    = verify_transaction(tx, auth_ca["signature"], ENROLLED_PUBKEY)
    check("C1  CLEARED doc full pipeline → Chip A APPROVED",
          result["status"] == "CLEARED" and ok_a,
          f"compliance={result['status']}  puf_verify={ok_a}")
except Exception as e:
    check("C1  CLEARED doc full pipeline", False, str(e)[:120])

# C2: First REJECTED doc — compliance must reject before PUF is ever called
rejected_doc = next(d for d in docs if d["swift"]["anomaly_injected"])
try:
    parsed  = parse_document(rejected_doc["swift"])
    result  = check_compliance(rejected_doc["swift"], rejected_doc["bill_of_lading"], parsed)
    check("C2  REJECTED doc — compliance blocks before PUF",
          result["status"] == "REJECTED",
          f"compliance={result['status']}  issues={result['issues']}")
except Exception as e:
    check("C2  REJECTED doc compliance check", False, str(e)[:120])

# C3: Chip B on CLEARED doc — compliance CLEARED but PUF BLOCKED
try:
    tx_c = build_tx(cleared_doc["swift"], note="CLONE-ATTACK")
    ab   = sign_transaction(tx_c, chip="B")
    ok_b = verify_transaction(tx_c, ab["signature"], ENROLLED_PUBKEY)
    check("C3  CLEARED doc + Chip B → compliance OK but PUF BLOCKED",
          not ok_b,
          f"verified={ok_b} (expected False — clone attack caught at signing layer)")
except Exception as e:
    check("C3  Chip B clone on CLEARED doc", False, str(e)[:120])

# C4: FLAGGED doc — compliance returns FLAGGED (officer required), not REJECTED
flagged_doc = next(
    d for d in docs
    if not d["swift"]["anomaly_injected"] and d["swift"]["amount_usd"] > 200000
)
try:
    parsed = parse_document(flagged_doc["swift"])
    result = check_compliance(flagged_doc["swift"], flagged_doc["bill_of_lading"], parsed)
    check("C4  FLAGGED doc — compliance returns FLAGGED  (human gate required)",
          result["status"] == "FLAGGED",
          f"compliance={result['status']}  amount={flagged_doc['swift']['amount_usd']:,}")
except Exception as e:
    check("C4  FLAGGED doc compliance check", False, str(e)[:120])

# ─────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────
total = PASS_COUNT + FAIL_COUNT
print(f"\n{'=' * 64}")
print(f"  CRITICAL TESTS: {PASS_COUNT}/{total} passed", end="  ")
if FAIL_COUNT == 0:
    print("— ALL CRITICAL TESTS PASSED ✓")
else:
    print(f"— {FAIL_COUNT} CRITICAL FAILURE(S) — review above")
print(f"{'=' * 64}\n")

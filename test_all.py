"""
PUF-Pay — Full Pipeline Test Suite
GIFT IFIH Young Builders Program 2026
"""
import sys, os, json, subprocess

sys.stdout.reconfigure(encoding="utf-8")

sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))
from agent1_parser    import parse_document
from agent2_compliance import check_compliance
from agent3_puf_auth  import sign_transaction, verify_transaction

PASS = "  PASS"
FAIL = "  FAIL"
SEP  = "-" * 60

def header(title):
    print(f"\n{SEP}")
    print(f"  {title}")
    print(SEP)

def result(label, ok, detail=""):
    icon = "[PASS]" if ok else "[FAIL]"
    line = f"{icon}  {label}"
    if detail:
        line += f"\n        {detail}"
    print(line)
    return ok


with open("synthetic_docs.json") as f:
    docs = json.load(f)

all_passed = True

# ─────────────────────────────────────────────────────────
# TEST 1 — Bedrock Connection
# ─────────────────────────────────────────────────────────
header("TEST 1 — AWS Bedrock Connection")

try:
    import boto3
    client = boto3.client("bedrock-runtime", region_name="us-east-1")
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 10,
        "messages": [{"role": "user", "content": "Reply: OK"}],
    })
    resp = client.invoke_model(
        modelId="us.anthropic.claude-sonnet-4-6",
        contentType="application/json",
        accept="application/json",
        body=body,
    )
    text = json.loads(resp["body"].read())["content"][0]["text"]
    ok = len(text) > 0
    all_passed &= result("Bedrock API reachable (us-east-1, claude-sonnet-4-6)", ok,
                         f"Response: {text[:60]}")
except Exception as e:
    all_passed &= result("Bedrock API reachable", False, str(e)[:120])

# ─────────────────────────────────────────────────────────
# TEST 2 — Agent 1: Parse 3 documents
# ─────────────────────────────────────────────────────────
header("TEST 2 — Agent 1: Document Parsing (3 docs)")

for i in range(3):
    swift = docs[i]["swift"]
    try:
        parsed = parse_document(swift)
        required = ["applicant", "beneficiary", "amount_usd", "goods",
                    "port_of_loading", "port_of_discharge", "issue_date", "expiry_date", "summary"]
        missing = [k for k in required if k not in parsed or not str(parsed[k]).strip()]
        ok = len(missing) == 0
        detail = (f"summary: {str(parsed.get('summary',''))[:60]}"
                  if ok else f"missing fields: {missing}")
        all_passed &= result(f"LC-{i+1} ({swift['doc_id']}) parsed", ok, detail)
    except Exception as e:
        all_passed &= result(f"LC-{i+1} ({swift['doc_id']}) parsed", False, str(e)[:120])

# ─────────────────────────────────────────────────────────
# TEST 3 — Agent 2: Compliance on all 10 docs
# ─────────────────────────────────────────────────────────
header("TEST 3 — Agent 2: Compliance Check (all 10 docs)")

VALID_STATUSES = {"CLEARED", "FLAGGED", "REJECTED"}
parsed_cache = {}

for i, doc in enumerate(docs):
    swift = doc["swift"]
    bl    = doc["bill_of_lading"]
    try:
        # Parse first (reuse if already done)
        if i < 3 and i in parsed_cache:
            parsed = parsed_cache[i]
        else:
            parsed = parse_document(swift)
            parsed_cache[i] = parsed

        result_c = check_compliance(swift, bl, parsed)
        status   = result_c.get("status", "")
        ok       = status in VALID_STATUSES
        detail   = f"status={status} | issues={len(result_c.get('issues',[]))}"
        all_passed &= result(f"LC-{i+1} ({swift['doc_id']}) compliance", ok, detail)
    except Exception as e:
        all_passed &= result(f"LC-{i+1} ({swift['doc_id']}) compliance", False, str(e)[:120])

# ─────────────────────────────────────────────────────────
# TEST 4 — Agent 3: Chip A → APPROVED
# ─────────────────────────────────────────────────────────
header("TEST 4 — Agent 3: Chip A signing (expect APPROVED)")

try:
    enrolled_pubkey = sign_transaction("ENROLLMENT", chip="A")["public_key"]
    tx = "APPROVE LC TEST-001 | USD 150000 | AUTO-CLEARED"
    auth_a   = sign_transaction(tx, chip="A")
    verified = verify_transaction(tx, auth_a["signature"], enrolled_pubkey)
    ok = verified is True
    all_passed &= result("Chip A signature verifies against enrolled pubkey", ok,
                         f"verified={verified}")
except Exception as e:
    all_passed &= result("Chip A signing", False, str(e)[:120])

# ─────────────────────────────────────────────────────────
# TEST 5 — Agent 3: Chip B → BLOCKED (clone attack)
# ─────────────────────────────────────────────────────────
header("TEST 5 — Agent 3: Chip B clone attack (expect BLOCKED)")

try:
    enrolled_pubkey = sign_transaction("ENROLLMENT", chip="A")["public_key"]
    tx = "APPROVE LC TEST-001 | USD 150000 | AUTO-CLEARED"
    auth_b   = sign_transaction(tx, chip="B")
    verified = verify_transaction(tx, auth_b["signature"], enrolled_pubkey)
    ok = verified is False  # clone must NOT pass enrolled key check
    all_passed &= result("Chip B signature rejected (clone detected)", ok,
                         f"verified={verified}  — expected False")
except Exception as e:
    all_passed &= result("Chip B clone attack", False, str(e)[:120])

# ─────────────────────────────────────────────────────────
# TEST 6 — app.py syntax check
# ─────────────────────────────────────────────────────────
header("TEST 6 — app.py Syntax Check")

try:
    proc = subprocess.run(
        [sys.executable, "-m", "py_compile", "app.py"],
        capture_output=True, text=True, timeout=15
    )
    ok = proc.returncode == 0
    detail = proc.stderr.strip()[:200] if not ok else "No syntax errors"
    all_passed &= result("app.py compiles without errors", ok, detail)
except Exception as e:
    all_passed &= result("app.py syntax check", False, str(e)[:120])

# ─────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
if all_passed:
    print("  ALL TESTS PASSED — pipeline is submission-ready")
else:
    print("  SOME TESTS FAILED — see details above")
print(f"{'=' * 60}\n")

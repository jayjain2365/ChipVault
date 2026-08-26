"""
local_inference.py — PUF-Pay on-device inference engine
=======================================================
Drop-in replacement for the two AWS Bedrock calls that used to live in
agent1_parser.py (document parsing) and agent2_compliance.py (compliance memo).

Why this exists
---------------
Bedrock is no longer available to this project, which broke Agent 1 and the
Agent 2 memo. The four IFSCA compliance *rules* and the whole PUF/ECDSA layer
were always local and unaffected — only these two LLM touch-points needed a
replacement. This module provides that replacement.

Design goals
------------
1. ZERO cloud dependency by default. The app boots and runs the full pipeline
   with no API key, no internet and no AWS account — so a live jury demo can
   never fail on a flaky network.
2. Same public API as the old agents: `parse_document(doc)` and
   `check_compliance(swift, bl, parsed)` return the same-shaped dicts, so app.py
   only needs to change its import line.
3. Optional real-LLM upgrade. If a GROQ_API_KEY (free tier) or ANTHROPIC_API_KEY
   is present in the environment or Streamlit secrets, the compliance *memo* is
   written by a live model. If that call fails for ANY reason, we silently fall
   back to the deterministic memo — the pipeline is always bulletproof.

The four IFSCA compliance RULES are always deterministic (exactly as before);
only the natural-language memo is optionally LLM-generated.
"""

import os
import json

# ── Optional LLM configuration ────────────────────────────────────────────────
_GROQ_KEY_NAMES      = ("GROQ_API_KEY",)
_ANTHROPIC_KEY_NAMES = ("ANTHROPIC_API_KEY",)


def _secret(*names):
    """Return the first non-empty value found in env vars or Streamlit secrets."""
    for n in names:
        v = os.environ.get(n)
        if v:
            return v.strip()
    # Streamlit secrets — only if streamlit is importable and configured.
    try:
        import streamlit as st
        for n in names:
            if n in st.secrets:
                return str(st.secrets[n]).strip()
            if "llm" in st.secrets and n in st.secrets["llm"]:
                return str(st.secrets["llm"][n]).strip()
    except Exception:
        pass
    return None


def ai_mode() -> dict:
    """Describe the active inference backend, for honest UI labelling.

    Returns a dict: {"mode": "llm"|"offline", "provider": str, "label": str}.
    """
    if _secret(*_GROQ_KEY_NAMES):
        return {"mode": "llm", "provider": "groq", "label": "Groq Llama-3.1 (live)"}
    if _secret(*_ANTHROPIC_KEY_NAMES):
        return {"mode": "llm", "provider": "anthropic", "label": "Claude (live)"}
    return {"mode": "offline", "provider": "on-device", "label": "On-Device Engine"}


# ── Agent 1 replacement — document parsing ─────────────────────────────────────
def parse_document(doc: dict) -> dict:
    """Extract the canonical field set from a SWIFT MT700 record.

    The SWIFT record is already structured, so extraction is deterministic: we
    map it to the downstream schema and compose a human-readable summary. This
    returns the exact shape the old Bedrock parser produced, so nothing
    downstream needs to change.
    """
    amount      = doc.get("amount_usd", 0) or 0
    currency    = doc.get("currency", "USD")
    applicant   = doc.get("applicant", "—")
    beneficiary = doc.get("beneficiary", "—")
    goods       = doc.get("goods_description", doc.get("goods", "—"))
    pol         = doc.get("port_of_loading", "—")
    pod         = doc.get("port_of_discharge", "—")
    issue       = doc.get("issue_date", "—")
    expiry      = doc.get("expiry_date", "—")

    try:
        amount_str = f"{float(amount):,.2f}"
    except (TypeError, ValueError):
        amount_str = str(amount)

    summary = (
        f"{applicant} opens a {currency} {amount_str} letter of credit in favour "
        f"of {beneficiary} for {goods}, shipped {pol} → {pod}; "
        f"valid {issue} to {expiry}."
    )

    return {
        "applicant":         applicant,
        "beneficiary":       beneficiary,
        "amount_usd":        amount,
        "currency":          currency,
        "goods":             goods,
        "port_of_loading":   pol,
        "port_of_discharge": pod,
        "issue_date":        issue,
        "expiry_date":       expiry,
        "summary":           summary,
    }


# ── Agent 2 replacement — IFSCA compliance (rules + memo) ──────────────────────
def check_compliance(swift: dict, bl: dict, parsed: dict) -> dict:
    """Run the four deterministic IFSCA rules, then attach a decision memo.

    Same logic and return shape as the original agent2_compliance.py. The rules
    are always deterministic; the memo is LLM-written only when a key is
    configured, otherwise a formal template memo is used.
    """
    issues = []

    # Rule 1: Expiry before issue date
    if swift["expiry_date"] < swift["issue_date"]:
        issues.append("CRITICAL: Expiry date is before issue date")

    # Rule 2: Goods mismatch between LC and BL
    if not bl["goods_match"]:
        issues.append("CRITICAL: Goods description mismatch between LC and Bill of Lading")

    # Rule 3: Amount threshold (IFSCA reporting above $200k)
    if swift["amount_usd"] > 200000:
        issues.append(f"FLAG: Amount USD {swift['amount_usd']:,.2f} exceeds IFSCA reporting threshold")

    # Rule 4: Port mismatch
    if swift["port_of_loading"] != bl["port_of_loading"]:
        issues.append("CRITICAL: Port of loading mismatch between LC and BL")

    status = "REJECTED" if any("CRITICAL" in i for i in issues) else \
             "FLAGGED" if issues else "CLEARED"

    memo = _generate_memo(status, issues, parsed.get("summary", ""))

    return {"status": status, "issues": issues, "compliance_memo": memo}


# ── Compliance memo generation ─────────────────────────────────────────────────
def _generate_memo(status: str, issues: list, summary: str) -> str:
    """LLM memo when a key is configured (with silent fallback); else template."""
    mode = ai_mode()
    if mode["mode"] == "llm":
        try:
            memo = _llm_memo(mode["provider"], status, issues, summary)
            if memo and memo.strip():
                return memo.strip()
        except Exception:
            pass  # any LLM failure → deterministic fallback below
    return _template_memo(status, issues)


def _template_memo(status: str, issues: list) -> str:
    """Formal, concise, status-aware compliance memo — no external calls."""
    if status == "CLEARED":
        return (
            "Compliance review complete. All IFSCA trade-finance checks — date "
            "validity, LC/BL goods concordance, reporting threshold and port "
            "consistency — have passed. The transaction is cleared for "
            "PUF-authenticated settlement."
        )
    if status == "FLAGGED":
        flags = "; ".join(
            i.split("FLAG:", 1)[-1].strip() for i in issues if "FLAG" in i
        )
        return (
            "Compliance review complete. No critical discrepancies were found; "
            f"however the transaction is escalated for officer review "
            f"({flags or 'threshold review'}). Manual authorisation is required "
            "before PUF settlement."
        )
    # REJECTED
    crit = next(
        (i.split("CRITICAL:", 1)[-1].strip() for i in issues if "CRITICAL" in i),
        "a critical documentary discrepancy",
    )
    return (
        "Compliance review failed. A critical discrepancy was detected — "
        f"{crit}. Under IFSCA trade-finance controls this transaction is "
        "automatically blocked and may not proceed to settlement."
    )


def _llm_memo(provider: str, status: str, issues: list, summary: str):
    """Optional live-LLM memo via Groq (free) or Anthropic. stdlib-only (urllib).

    Returns the memo text, or None on any problem so the caller can fall back.
    """
    import urllib.request

    prompt = (
        "You are a GIFT City IFSCA compliance officer.\n\n"
        f"A trade finance document has been checked. Result: {status}\n"
        f"Issues found: {issues if issues else 'None'}\n"
        f"Transaction: {summary}\n\n"
        "Write a formal, concise 2-line compliance decision memo."
    )
    model = os.environ.get("LLM_MODEL")

    if provider == "groq":
        key = _secret(*_GROQ_KEY_NAMES)
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=json.dumps({
                "model": model or "llama-3.1-8b-instant",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 200,
                "temperature": 0.3,
            }).encode(),
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        return data["choices"][0]["message"]["content"]

    if provider == "anthropic":
        key = _secret(*_ANTHROPIC_KEY_NAMES)
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages",
            data=json.dumps({
                "model": model or "claude-3-5-sonnet-20241022",
                "max_tokens": 200,
                "messages": [{"role": "user", "content": prompt}],
            }).encode(),
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read())
        return data["content"][0]["text"]

    return None


# ── Self-test ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(here, "synthetic_docs.json")) as f:
        docs = json.load(f)

    print(f"Engine mode: {ai_mode()['label']}\n")
    tally = {"CLEARED": 0, "FLAGGED": 0, "REJECTED": 0}
    for i, d in enumerate(docs):
        parsed = parse_document(d["swift"])
        result = check_compliance(d["swift"], d["bill_of_lading"], parsed)
        tally[result["status"]] += 1
        print(f"LC-{i+1}: {result['status']}")
        for issue in result["issues"]:
            print(f"   -> {issue}")
    print(f"\nTotals: {tally}")

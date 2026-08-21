import streamlit as st
import json, sys, os, time, re
from datetime import datetime

sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))
from agent1_parser import parse_document
from agent2_compliance import check_compliance
from agent3_puf_auth import sign_transaction, verify_transaction

# ── Load data ─────────────────────────────────────────────────────────────────
with open("synthetic_docs.json") as f:
    docs = json.load(f)

# Chip A's enrolled public key — derived once at startup (this is what the bank stores)
_CHIP_A_PUBKEY = sign_transaction("ENROLLMENT", chip="A")["public_key"]

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PUF-Pay | GIFT City Trade Finance",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.html("""
<style>
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1400px; }

/* ─ Header ─ */
.puf-header {
    background: linear-gradient(135deg, #0c1c30 0%, #0f2d4a 60%, #0a1a2e 100%);
    border: 1px solid #1e3a5f;
    border-radius: 14px;
    padding: 22px 30px;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
}
.puf-header-title { font-size: 1.85rem; font-weight: 800; color: #e8f4f8; letter-spacing: -0.5px; margin: 0; }
.puf-header-sub   { color: #5a99c2; font-size: 0.82rem; margin-top: 3px; }
.puf-header-badges { display: flex; gap: 7px; flex-wrap: wrap; }
.badge {
    background: rgba(100,180,255,0.1);
    border: 1px solid rgba(100,180,255,0.22);
    color: #64b4ff;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    white-space: nowrap;
}

/* ─ Pipeline ─ */
.pipe-wrap {
    background: #0d1424;
    border: 1px solid #1a2740;
    border-radius: 14px;
    padding: 18px 28px;
    margin-bottom: 18px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.pipe-step {
    display: flex; flex-direction: column; align-items: center;
    gap: 6px; flex: 1; max-width: 170px;
}
.pipe-circle {
    width: 46px; height: 46px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 1rem; font-weight: 800; border: 2px solid;
}
.pc-pend { border-color:#2d3748; background:#1a2035; color:#4a5568; }
.pc-ok   { border-color:#059669; background:#052e16; color:#34d399; }
.pc-warn { border-color:#d97706; background:#3b1f00; color:#fcd34d; }
.pc-fail { border-color:#dc2626; background:#3b0000; color:#f87171; }

.pipe-label  { font-size:0.7rem; color:#718096; font-weight:500; text-align:center; line-height:1.3; }
.pipe-status { font-size:0.67rem; font-weight:700; text-align:center; letter-spacing:0.3px; }
.ps-pend { color:#4a5568; }
.ps-ok   { color:#10b981; }
.ps-warn { color:#f59e0b; }
.ps-fail { color:#ef4444; }

.pipe-arrow      { color:#1e2d42; font-size:1.3rem; padding: 0 10px; padding-bottom:18px; flex-shrink:0; }
.pipe-arrow.done { color:#059669; }

/* ─ Cards ─ */
.card {
    background: #0f1825;
    border: 1px solid #1a2740;
    border-radius: 12px;
    padding: 18px;
    margin-bottom: 14px;
}
.card-title {
    font-size: 0.7rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1.2px; color: #4a6080; margin-bottom: 14px;
    padding-bottom: 10px; border-bottom: 1px solid #1a2740;
}
.doc-id {
    display: inline-block;
    background: #0a0f1a; border: 1px solid #1e3a5f;
    color: #64b4ff; padding: 2px 10px; border-radius: 5px;
    font-family: monospace; font-size: 0.78rem; font-weight: 700;
    margin-bottom: 12px;
}
.field-row {
    display: flex; justify-content: space-between; align-items: baseline;
    padding: 5px 0; border-bottom: 1px solid #0a0f1a; gap: 12px;
}
.field-row:last-child { border-bottom: none; }
.fl { color: #4a6080; font-size: 0.72rem; white-space: nowrap; min-width: 110px; }
.fv { color: #cbd5e0; font-size: 0.77rem; text-align: right; max-width: 65%; word-break: break-word; }
.fv-amount { color: #34d399; font-weight: 700; font-size: 0.88rem; }
.fv-warn   { color: #fbbf24; font-weight: 600; }
.fv-bad    { color: #f87171; font-weight: 600; }
.fv-ok     { color: #34d399; font-weight: 600; }

/* ─ Issue pills ─ */
.pill-critical {
    display: inline-block; padding: 3px 10px; border-radius: 4px; margin: 2px 4px 2px 0;
    background: #3b0000; border: 1px solid #dc2626; color: #f87171;
    font-size: 0.72rem; font-weight: 600;
}
.pill-flag {
    display: inline-block; padding: 3px 10px; border-radius: 4px; margin: 2px 4px 2px 0;
    background: #3b1f00; border: 1px solid #d97706; color: #fcd34d;
    font-size: 0.72rem; font-weight: 600;
}

/* ─ Compliance memo ─ */
.memo-box {
    background: #080e1a; border: 1px solid #1e3a5f; border-radius: 8px;
    padding: 12px 16px; color: #8899aa; font-size: 0.77rem;
    line-height: 1.65; font-style: italic; margin-top: 12px;
}

/* ─ Signature ─ */
.sig-box {
    background: #060c18; border: 1px solid #1e3a5f; border-radius: 8px;
    padding: 12px 14px; font-family: monospace; font-size: 0.68rem;
    color: #4a8fbc; word-break: break-all; margin-top: 12px; line-height: 1.7;
}
.sig-label { color: #2d4a60; font-size: 0.65rem; }

/* ─ Final banners ─ */
.banner-approved {
    background: linear-gradient(135deg, #042214, #052e16);
    border: 1px solid #059669; border-radius: 14px;
    padding: 28px; text-align: center; margin-top: 16px;
}
.banner-blocked {
    background: linear-gradient(135deg, #280000, #3b0000);
    border: 1px solid #dc2626; border-radius: 14px;
    padding: 28px; text-align: center; margin-top: 16px;
}
.banner-rejected {
    background: #1a1200; border: 1px solid #78350f; border-radius: 14px;
    padding: 22px; text-align: center; margin-top: 16px;
}
.banner-title { font-size: 1.3rem; font-weight: 800; margin: 8px 0 4px; }
.banner-sub   { color: #718096; font-size: 0.8rem; }

/* ─ TX log ─ */
.tx-row {
    display: flex; align-items: center; justify-content: space-between;
    padding: 8px 14px; background: #0a0f1a; border-radius: 7px;
    margin-bottom: 4px; border-left: 3px solid; font-size: 0.73rem; gap: 10px;
}
.tx-row.ok   { border-left-color: #10b981; }
.tx-row.fail { border-left-color: #ef4444; }
.tx-row.rej  { border-left-color: #4a5568; }
.tx-doc  { color: #cbd5e0; font-family: monospace; font-weight: 700; }
.tx-amt  { color: #4a6080; flex: 1; }
.tx-res  { font-weight: 700; }
.tx-time { color: #2d3748; font-size: 0.65rem; }

/* ─ PUF explainer ─ */
.puf-explainer {
    background: #080e1a; border: 1px solid #1e3a5f; border-radius: 10px;
    padding: 14px 16px; font-size: 0.74rem; color: #6b7280; line-height: 1.7;
    margin-top: 12px;
}
.puf-explainer b { color: #64b4ff; }

/* ─ Blocked compliance box ─ */
.blocked-box {
    background: #1c0505; border: 1px solid #7f1d1d; border-radius: 10px;
    padding: 22px; text-align: center;
}

/* ─ Sidebar ─ */
section[data-testid="stSidebar"] { background: #070d1a; border-right: 1px solid #1a2740; }

/* ─ Buttons ─ */
div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #1e40af, #1d4ed8);
    border: none; border-radius: 8px; font-weight: 700;
    transition: all 0.15s;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    background: linear-gradient(135deg, #2563eb, #1e40af);
    box-shadow: 0 4px 14px rgba(59,130,246,0.35);
}
</style>
""")

# ── Helpers ───────────────────────────────────────────────────────────────────
def field(label, value, cls="fv"):
    return f'<div class="field-row"><span class="fl">{label}</span><span class="{cls}">{value}</span></div>'

def md_to_html(text):
    """Convert **bold** and *italic* Markdown to HTML so it renders in st.html()."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*',     r'<em>\1</em>',         text)
    return text

# ── Session state defaults ─────────────────────────────────────────────────────
if "tx_log"         not in st.session_state: st.session_state["tx_log"]         = []
if "payment_result" not in st.session_state: st.session_state["payment_result"] = None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.html("""
    <div style="text-align:center;padding:14px 0 18px">
        <div style="font-size:2rem">🔐</div>
        <div style="font-size:1.05rem;font-weight:800;color:#e2e8f0;margin-top:4px">PUF-Pay</div>
        <div style="font-size:0.68rem;color:#2d3748;margin-top:2px">GIFT City IBU Platform</div>
    </div>""")

    st.markdown("**Select Transaction**")
    doc_index = st.selectbox(
        "doc",
        range(10),
        format_func=lambda i: f"LC-{i+1}  ·  {docs[i]['swift']['applicant'][:22]}",
        label_visibility="collapsed",
    )

    st.markdown("**Officer Device**")
    chip_label = st.radio(
        "chip",
        ["A  —  Enrolled (Trusted)", "B  —  Cloned Device (Attack Demo)"],
        label_visibility="collapsed",
    )
    chip = "A" if chip_label.startswith("A") else "B"

    if chip == "A":
        st.html("""<div style="background:#042214;border:1px solid #059669;border-radius:7px;
            padding:9px 12px;font-size:0.73rem;color:#34d399;margin-top:4px;">
            ✓ Chip A · Enrolled trusted device<br>
            <span style="color:#065f46;font-size:0.67rem">SECP256k1 · PUF-derived key</span>
        </div>""")
    else:
        st.html("""<div style="background:#280000;border:1px solid #dc2626;border-radius:7px;
            padding:9px 12px;font-size:0.73rem;color:#f87171;margin-top:4px;">
            ⚠ Chip B · Simulates clone / attacker<br>
            <span style="color:#7f1d1d;font-size:0.67rem">Different silicon → different key</span>
        </div>""")

    st.divider()

    # Session stats
    log = st.session_state["tx_log"]
    c1, c2, c3 = st.columns(3)
    c1.metric("✅", sum(1 for t in log if t["result"] == "APPROVED"),  delta=None, help="Approved")
    c2.metric("🚫", sum(1 for t in log if t["result"] == "BLOCKED"),   delta=None, help="Blocked (clone)")
    c3.metric("❌", sum(1 for t in log if t["result"] == "REJECTED"),  delta=None, help="Rejected by officer")

    st.divider()

    st.html("""<div class="puf-explainer">
    <b>What is a PUF?</b><br>
    Every chip has microscopic silicon variations from manufacturing. A Ring Oscillator PUF
    measures these to generate a <b>unique 128-bit fingerprint</b> — never stored, regenerated
    on demand. A cloned device has different silicon → different key → signature fails.<br><br>
    <b>Hardware:</b> 256 Ring Oscillators · Fuzzy Extractor · Verilog / Vivado XSim<br>
    <b>AI:</b> AWS Bedrock · Claude Sonnet · IFSCA Compliance<br>
    <b>Crypto:</b> ECDSA SECP256k1
    </div>""")

# ── Load doc ──────────────────────────────────────────────────────────────────
doc            = docs[doc_index]
swift          = doc["swift"]
bl             = doc["bill_of_lading"]
current_doc_id = swift["doc_id"]

# ── Reset state on doc / chip change ─────────────────────────────────────────
doc_changed  = st.session_state.get("current_doc_id") != current_doc_id
chip_changed = st.session_state.get("current_chip")   != chip

if doc_changed or chip_changed:
    for k in ["payment_result", "puf_auth", "tx_string"]:
        st.session_state.pop(k, None)
    st.session_state["payment_result"] = None

    if doc_changed:
        for k in ["parsed", "compliance", "pipeline_done", "pipeline_error"]:
            st.session_state.pop(k, None)
    elif chip_changed:
        st.session_state.pop("pipeline_error", None)
        # CLEARED docs: re-run PUF automatically with the new chip
        current_comp = st.session_state.get("compliance", {}).get("status")
        if current_comp == "CLEARED":
            st.session_state.pop("pipeline_done", None)
        # FLAGGED/REJECTED: keep pipeline_done — only payment decision needs resetting

    st.session_state["current_doc_id"] = current_doc_id
    st.session_state["current_chip"]   = chip

ss = st.session_state

# ── Header ────────────────────────────────────────────────────────────────────
st.html(f"""
<div class="puf-header">
    <div>
        <div class="puf-header-title">🔐 PUF-Pay</div>
        <div class="puf-header-sub">Secure Trade Finance · GIFT City IBU · "Your silicon is your password."</div>
    </div>
    <div class="puf-header-badges">
        <span class="badge">AWS Bedrock</span>
        <span class="badge">Claude Sonnet</span>
        <span class="badge">Ring-Osc PUF</span>
        <span class="badge">ECDSA SECP256k1</span>
        <span class="badge">IFSCA Compliance</span>
        <span class="badge">LC: {current_doc_id}</span>
    </div>
</div>""")

# ── Compute pipeline display states ───────────────────────────────────────────
parsed_done      = "parsed" in ss
compliance_done  = "compliance" in ss
compliance_status = ss["compliance"]["status"] if compliance_done else None
pr               = ss.get("payment_result")

s1_cc, s1_t = ("ok", "PARSED") if parsed_done else ("pend", "PENDING")

if compliance_done:
    s2_cc = {"CLEARED": "ok", "FLAGGED": "warn", "REJECTED": "fail"}[compliance_status]
    s2_t  = compliance_status
else:
    s2_cc, s2_t = "pend", "PENDING"

# Step 3 — human gate (only relevant for FLAGGED)
if compliance_done and compliance_status == "REJECTED":
    s3_cc, s3_t = "fail", "BLOCKED"
elif pr in ("APPROVED", "BLOCKED"):
    s3_cc, s3_t = "ok", "SIGNED"
elif pr == "REJECTED":
    s3_cc, s3_t = "fail", "REJECTED"
elif compliance_done and compliance_status == "CLEARED":
    s3_cc, s3_t = "ok", "AUTO"
else:
    s3_cc, s3_t = "pend", "PENDING"

# Step 4 — PUF auth
if compliance_done and compliance_status == "REJECTED":
    s4_cc, s4_t = "fail", "BLOCKED"
elif pr == "APPROVED":
    s4_cc, s4_t = "ok", "CHIP A ✓"
elif pr == "BLOCKED":
    s4_cc, s4_t = "fail", "CHIP B ✗"
elif pr == "REJECTED":
    s4_cc, s4_t = "pend", "N/A"
else:
    s4_cc, s4_t = "pend", "PENDING"

a1_col = "#059669" if parsed_done     else "#1e2d42"
a2_col = "#059669" if compliance_done else "#1e2d42"
a3_col = "#059669" if pr in ("APPROVED", "BLOCKED", "REJECTED") else "#1e2d42"

COLORS = {
    "pend": {"bg": "#1a2035", "bd": "#2d3748", "fg": "#4a5568", "st": "#4a5568"},
    "ok":   {"bg": "#052e16", "bd": "#059669", "fg": "#34d399", "st": "#10b981"},
    "warn": {"bg": "#3b1f00", "bd": "#d97706", "fg": "#fcd34d", "st": "#f59e0b"},
    "fail": {"bg": "#3b0000", "bd": "#dc2626", "fg": "#f87171", "st": "#ef4444"},
}

def circle(num, label, state, status):
    c = COLORS[state]
    return (
        f'<div style="display:flex;flex-direction:column;align-items:center;gap:6px;flex:1;max-width:160px;">'
        f'<div style="width:46px;height:46px;border-radius:50%;display:flex;align-items:center;'
        f'justify-content:center;font-size:1rem;font-weight:800;border:2px solid {c["bd"]};'
        f'background:{c["bg"]};color:{c["fg"]};">{num}</div>'
        f'<div style="font-size:0.7rem;color:#718096;text-align:center;line-height:1.3;">{label}</div>'
        f'<div style="font-size:0.68rem;font-weight:700;text-align:center;color:{c["st"]};">{status}</div>'
        f'</div>'
    )

def arrow(col):
    return f'<div style="color:{col};font-size:1.3rem;padding:0 8px;padding-bottom:18px;flex-shrink:0;">&#8594;</div>'

pipe_html = (
    f'<div style="display:flex;align-items:center;justify-content:center;background:#0d1424;'
    f'border:1px solid #1a2740;border-radius:14px;padding:18px 28px;margin-bottom:18px;">'
    f'{circle("&#9312;", "AI Document Parse",  s1_cc, s1_t)}'
    f'{arrow(a1_col)}'
    f'{circle("&#9313;", "IFSCA Compliance",   s2_cc, s2_t)}'
    f'{arrow(a2_col)}'
    f'{circle("&#9314;", "Human Approval",     s3_cc, s3_t)}'
    f'{arrow(a3_col)}'
    f'{circle("&#9315;", "PUF Authentication", s4_cc, s4_t)}'
    f'</div>'
)
st.html(pipe_html)

# ── Documents ─────────────────────────────────────────────────────────────────
col_l, col_r = st.columns(2)

with col_l:
    amt_cls  = "fv-amount" + (" fv-warn" if swift["amount_usd"] > 200000 else "")
    amt_note = "  ⚠ > $200k threshold" if swift["amount_usd"] > 200000 else ""
    exp_cls  = "fv-bad" if swift["expiry_date"] < swift["issue_date"] else "fv"

    st.html(f"""
    <div class="card">
        <div class="card-title">📄 SWIFT MT700 — Letter of Credit</div>
        <div class="doc-id">{swift['doc_id']}</div>
        {field("Applicant",    swift['applicant'])}
        {field("Beneficiary",  swift['beneficiary'])}
        {field("Issuing Bank", swift['issuing_bank'])}
        {field("Amount (USD)", f"$ {swift['amount_usd']:,.2f}{amt_note}", amt_cls)}
        {field("Goods",        swift['goods_description'])}
        {field("Route",        f"{swift['port_of_loading']} → {swift['port_of_discharge']}")}
        {field("Issue Date",   swift['issue_date'])}
        {field("Expiry Date",  swift['expiry_date'], exp_cls)}
    </div>""")

with col_r:
    port_cls  = "fv-bad" if bl["port_of_loading"] != swift["port_of_loading"] else "fv-ok"
    port_note = "  ⚠ MISMATCH" if bl["port_of_loading"] != swift["port_of_loading"] else "  ✓"
    goods_cls = "fv-bad" if not bl["goods_match"] else "fv-ok"
    goods_val = "✓ Match" if bl["goods_match"] else "✗ MISMATCH"

    st.html(f"""
    <div class="card">
        <div class="card-title">🚢 Bill of Lading</div>
        <div class="doc-id">{bl['bl_number']}</div>
        {field("Linked LC",         bl['linked_lc'])}
        {field("Vessel",            f"{bl['vessel']}  ·  {bl['voyage_no']}")}
        {field("Shipper",           bl['shipper'])}
        {field("Consignee",         bl['consignee'])}
        {field("Port of Loading",   bl['port_of_loading'] + port_note, port_cls)}
        {field("Port of Discharge", bl['port_of_discharge'])}
        {field("Goods Match",       goods_val, goods_cls)}
        {field("Weight",            f"{bl['gross_weight_kg']:,} kg  ·  {bl['containers']} containers")}
        {field("BL Date",           bl['bl_date'])}
    </div>""")

# ── Auto-pipeline ─────────────────────────────────────────────────────────────
if "pipeline_done" not in ss:
    needs_agents = "parsed" not in ss or "compliance" not in ss

    with st.status("🔄 Running security pipeline...", expanded=True) as status_box:
        try:
            if needs_agents:
                st.write("🤖 Agent 1 — Parsing document via AWS Bedrock...")
                time.sleep(1)
                parsed = parse_document(swift)
                ss["parsed"] = parsed
                st.write(f"   ✅ Parsed — {parsed.get('summary', '')[:80]}")

                time.sleep(1.5)
                st.write("🔍 Agent 2 — Running IFSCA compliance check...")
                result = check_compliance(swift, bl, parsed)
                ss["compliance"] = result
                n = len(result["issues"])
                issue_str = f" ({n} issue{'s' if n != 1 else ''})" if n else ""
                st.write(f"   ✅ Compliance decision: {result['status']}{issue_str}")

            comp_status = ss["compliance"]["status"]

            if comp_status == "CLEARED":
                time.sleep(1)
                st.write(f"🔐 PUF Authentication — Chip {chip}...")
                tx = (
                    f"APPROVE LC {swift['doc_id']} | "
                    f"USD {swift['amount_usd']} | AUTO-CLEARED"
                )
                auth     = sign_transaction(tx, chip=chip)
                verified = verify_transaction(tx, auth["signature"], _CHIP_A_PUBKEY)
                ss["payment_result"] = "APPROVED" if verified else "BLOCKED"
                ss["puf_auth"]       = auth
                ss["tx_string"]      = tx
                ss["tx_log"].append({
                    "doc_id": swift["doc_id"],
                    "amount": swift["amount_usd"],
                    "chip":   chip,
                    "result": ss["payment_result"],
                    "time":   datetime.now().strftime("%H:%M:%S"),
                })
                if verified:
                    st.write(f"   ✅ Chip {chip} authenticated — payment authorised")
                    status_box.update(label="Pipeline complete — APPROVED ✅", state="complete")
                else:
                    st.write(f"   🚫 Chip {chip} rejected — clone attack detected")
                    status_box.update(label="Pipeline complete — BLOCKED 🚫", state="complete")

            elif comp_status == "FLAGGED":
                time.sleep(0.5)
                st.write("⚠️ Transaction flagged — officer review required before signing")
                status_box.update(label="⚠️ Awaiting officer approval", state="running")

            else:  # REJECTED
                time.sleep(0.5)
                st.write("❌ Critical compliance failures — transaction blocked automatically")
                status_box.update(
                    label="❌ Transaction rejected by compliance engine", state="error"
                )

        except Exception as e:
            ss["pipeline_error"] = str(e)[:300]
            status_box.update(label="⚠️ Pipeline error — check AWS credentials", state="error")

        ss["pipeline_done"] = True

    st.rerun()

# ── Pipeline error banner ──────────────────────────────────────────────────────
if ss.get("pipeline_error"):
    st.error(
        f"Pipeline error: {ss['pipeline_error']}\n\n"
        "Check AWS credentials / Bedrock access, then select a different document to retry."
    )

# ── Agent 1 result ────────────────────────────────────────────────────────────
if "parsed" in ss:
    p = ss["parsed"]
    with st.expander("Agent 1 — Parsed Fields  (AWS Bedrock output)", expanded=False):
        g1, g2 = st.columns(2)
        with g1:
            st.html(f"""
            <div style="font-size:0.77rem;line-height:2">
                <span style="color:#4a6080">Applicant:</span>  <span style="color:#cbd5e0">{p.get('applicant','—')}</span><br>
                <span style="color:#4a6080">Beneficiary:</span> <span style="color:#cbd5e0">{p.get('beneficiary','—')}</span><br>
                <span style="color:#4a6080">Amount:</span> <span style="color:#34d399;font-weight:700">USD {p.get('amount_usd','—')}</span><br>
                <span style="color:#4a6080">Currency:</span> <span style="color:#cbd5e0">{p.get('currency','—')}</span>
            </div>""")
        with g2:
            st.html(f"""
            <div style="font-size:0.77rem;line-height:2">
                <span style="color:#4a6080">Port of Loading:</span>  <span style="color:#cbd5e0">{p.get('port_of_loading','—')}</span><br>
                <span style="color:#4a6080">Port of Discharge:</span> <span style="color:#cbd5e0">{p.get('port_of_discharge','—')}</span><br>
                <span style="color:#4a6080">Issue Date:</span> <span style="color:#cbd5e0">{p.get('issue_date','—')}</span><br>
                <span style="color:#4a6080">Expiry Date:</span> <span style="color:#cbd5e0">{p.get('expiry_date','—')}</span>
            </div>""")
        st.html(f"""
        <div style="margin-top:10px;padding:10px 14px;background:#060c18;border:1px solid #1e3a5f;
             border-radius:7px;font-size:0.76rem;color:#8899aa;line-height:1.6;">
            <span style="color:#3a6080">AI Summary: </span>{p.get('summary','—')}
        </div>""")

# ── Agent 2 result ────────────────────────────────────────────────────────────
if "compliance" in ss:
    result = ss["compliance"]
    status = result["status"]
    icon   = {"CLEARED": "✅", "FLAGGED": "⚠️", "REJECTED": "❌"}[status]
    s_col  = {"CLEARED": "#10b981", "FLAGGED": "#f59e0b", "REJECTED": "#ef4444"}[status]

    issues_html = ""
    for issue in result["issues"]:
        cls = "pill-critical" if "CRITICAL" in issue else "pill-flag"
        issues_html += f'<span class="{cls}">{issue}</span> '
    if not issues_html:
        issues_html = '<span style="color:#10b981;font-size:0.78rem">No compliance issues found.</span>'

    with st.expander(f"Agent 2 — Compliance Result:  {status}", expanded=True):
        st.html(f"""
        <div style="display:flex;align-items:center;gap:14px;margin-bottom:14px;">
            <span style="font-size:1.9rem">{icon}</span>
            <span style="font-size:1.5rem;font-weight:800;color:{s_col}">{status}</span>
            <span style="font-size:0.75rem;color:#4a6080;align-self:flex-end;padding-bottom:4px">
                IFSCA trade finance compliance check
            </span>
        </div>
        <div style="margin-bottom:4px">{issues_html}</div>
        <div class="memo-box">📋 {md_to_html(result['compliance_memo'])}</div>
        """)

# ── Human-in-the-loop (FLAGGED only) ─────────────────────────────────────────
if compliance_done:
    if compliance_status == "REJECTED":
        st.divider()
        st.html("""
        <div class="blocked-box">
            <div style="font-size:2rem">🚫</div>
            <div style="font-size:1.05rem;font-weight:700;color:#ef4444;margin:8px 0 4px">
                Transaction Blocked by Compliance Engine
            </div>
            <div style="color:#718096;font-size:0.8rem">
                Critical compliance issues prevent this transaction from proceeding.<br>
                Human approval and PUF authentication are not available.
            </div>
        </div>""")

    elif compliance_status == "FLAGGED" and pr is None:
        st.divider()
        st.markdown("### 👤 Officer Approval Required")
        st.warning("⚠️ This transaction is **FLAGGED** — review compliance issues above before approving.")

        officer_note = st.text_input(
            "Officer Note",
            placeholder="e.g. Goods manifest verified against shipping records — approved for payment",
            key=f"note_{current_doc_id}",
        )

        ca, cr = st.columns(2)

        with ca:
            if st.button("✅  Approve & Sign with PUF", use_container_width=True, type="primary"):
                tx_string = (
                    f"APPROVE LC {swift['doc_id']} | "
                    f"USD {swift['amount_usd']} | "
                    f"OFFICER: {officer_note or 'approved'}"
                )
                try:
                    auth     = sign_transaction(tx_string, chip=chip)
                    verified = verify_transaction(tx_string, auth["signature"], _CHIP_A_PUBKEY)
                    ss["payment_result"] = "APPROVED" if verified else "BLOCKED"
                    ss["puf_auth"]       = auth
                    ss["tx_string"]      = tx_string
                    ss["tx_log"].append({
                        "doc_id": swift["doc_id"],
                        "amount": swift["amount_usd"],
                        "chip":   chip,
                        "result": ss["payment_result"],
                        "time":   datetime.now().strftime("%H:%M:%S"),
                    })
                    st.rerun()
                except Exception as e:
                    st.error(f"PUF signing error — {str(e)[:200]}")

        with cr:
            if st.button("❌  Reject Transaction", use_container_width=True):
                ss["payment_result"] = "REJECTED"
                ss["tx_log"].append({
                    "doc_id": swift["doc_id"],
                    "amount": swift["amount_usd"],
                    "chip":   chip,
                    "result": "REJECTED",
                    "time":   datetime.now().strftime("%H:%M:%S"),
                })
                st.rerun()

# ── Final result banners ──────────────────────────────────────────────────────
pr = ss.get("payment_result")

if pr == "APPROVED" and "puf_auth" in ss:
    auth = ss["puf_auth"]
    st.html(f"""
    <div class="banner-approved">
        <div style="font-size:2.5rem">✅</div>
        <div class="banner-title" style="color:#34d399">Payment Authorised</div>
        <div class="banner-sub">
            LC {swift['doc_id']}  ·  USD {swift['amount_usd']:,.2f}  ·  Chip A PUF Authenticated
        </div>
        <div class="sig-box">
            <span class="sig-label">TX STRING:  </span>{ss.get('tx_string','')}<br>
            <span class="sig-label">SIGNATURE:  </span>{auth['signature'][:96]}…<br>
            <span class="sig-label">PUBLIC KEY: </span>{auth['public_key'][:96]}…<br>
            <span style="color:#1e3a5f;font-size:0.62rem">
                ↑ ECDSA SECP256k1 · Private key regenerated from silicon PUF at signing time — never stored in memory
            </span>
        </div>
    </div>""")

elif pr == "BLOCKED":
    st.html(f"""
    <div class="banner-blocked">
        <div style="font-size:2.5rem">🚫</div>
        <div class="banner-title" style="color:#f87171">Clone Attack Detected — Payment Blocked</div>
        <div class="banner-sub">
            Chip B has different silicon → different PUF key → ECDSA signature fails Chip A's public key verification
        </div>
        <div style="margin-top:16px;display:flex;justify-content:center;gap:32px;font-size:0.78rem;color:#718096">
            <div>🔬 Different oscillator frequencies</div>
            <div>→</div>
            <div>🔑 Different 128-bit key</div>
            <div>→</div>
            <div>❌ Invalid signature</div>
        </div>
    </div>""")

elif pr == "REJECTED":
    st.html("""
    <div class="banner-rejected">
        <div style="font-size:1.8rem">❌</div>
        <div class="banner-title" style="color:#f59e0b">Transaction Rejected by Officer</div>
        <div class="banner-sub">PUF authentication was not executed.</div>
    </div>""")

# ── Transaction log ───────────────────────────────────────────────────────────
if ss["tx_log"]:
    st.divider()
    st.markdown("#### 📋 Session Transaction Log")
    rows = ""
    for t in reversed(ss["tx_log"]):
        row_cls = {"APPROVED": "ok", "BLOCKED": "fail", "REJECTED": "rej"}[t["result"]]
        res_col = {"APPROVED": "#10b981", "BLOCKED": "#ef4444", "REJECTED": "#f59e0b"}[t["result"]]
        em      = {"APPROVED": "✅", "BLOCKED": "🚫", "REJECTED": "❌"}[t["result"]]
        rows   += f"""
        <div class="tx-row {row_cls}">
            <span class="tx-doc">{t['doc_id']}</span>
            <span class="tx-amt">USD {t['amount']:>12,.0f}</span>
            <span style="color:#4a6080;font-size:0.71rem">Chip {t['chip']}</span>
            <span class="tx-res" style="color:{res_col}">{em} {t['result']}</span>
            <span class="tx-time">{t['time']}</span>
        </div>"""
    st.html(rows)

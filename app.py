import streamlit as st
import json, sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))
from agent1_parser import parse_document
from agent2_compliance import check_compliance
from agent3_puf_auth import sign_transaction, verify_transaction

with open("synthetic_docs.json") as f:
    docs = json.load(f)

st.set_page_config(page_title="PUF-Pay Trade Finance", page_icon="🔐", layout="wide")
st.title("🔐 PUF-Pay — Secure Trade Finance Platform")
st.caption("GIFT City IBU | Powered by AWS Bedrock + Hardware PUF Authentication")
st.divider()

# Sidebar
st.sidebar.header("Select Transaction")
doc_index = st.sidebar.selectbox(
    "Choose Document",
    range(10),
    format_func=lambda i: f"LC-{i+1}: {docs[i]['swift']['applicant'][:20]}"
)
chip = st.sidebar.radio(
    "Officer Device", ["A", "B"],
    help="Chip B simulates a cloned/compromised device"
)

doc = docs[doc_index]
current_doc_id = doc["swift"]["doc_id"]

# Reset all pipeline state when a different transaction is selected
if st.session_state.get("current_doc_id") != current_doc_id:
    for key in ["parsed", "compliance", "payment_result"]:
        st.session_state.pop(key, None)
    st.session_state["current_doc_id"] = current_doc_id

if "payment_result" not in st.session_state:
    st.session_state["payment_result"] = None

# Raw documents
col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 SWIFT MT700 — Letter of Credit")
    st.json(doc["swift"])
with col2:
    st.subheader("🚢 Bill of Lading")
    st.json(doc["bill_of_lading"])

st.divider()

# ── Pipeline status ──────────────────────────────────────────────────────────
st.subheader("⚡ Transaction Security Pipeline")

compliance_done = "compliance" in st.session_state
compliance_status = st.session_state["compliance"]["status"] if compliance_done else None
pr = st.session_state["payment_result"]

col1, col2, col3, col4 = st.columns(4)

with col1:
    if "parsed" in st.session_state:
        st.success("① Agent 1\n\nDocument Parsed")
    else:
        st.info("① Agent 1\n\nPending")

with col2:
    if compliance_done:
        if compliance_status == "CLEARED":
            st.success("② Agent 2\n\nCLEARED")
        elif compliance_status == "FLAGGED":
            st.warning("② Agent 2\n\nFLAGGED")
        else:
            st.error("② Agent 2\n\nREJECTED")
    else:
        st.info("② Agent 2\n\nPending")

with col3:
    if compliance_done and compliance_status == "REJECTED":
        st.error("③ Human Approval\n\nNOT EXECUTED")
    elif pr in ("APPROVED", "BLOCKED"):
        st.success("③ Human Approval\n\nAPPROVED")
    elif pr == "REJECTED":
        st.error("③ Human Approval\n\nREJECTED")
    else:
        st.info("③ Human Approval\n\nPending")

with col4:
    if compliance_done and compliance_status == "REJECTED":
        st.error("④ PUF Auth\n\nNOT EXECUTED")
    elif pr == "APPROVED":
        st.success("④ PUF Auth\n\nCHIP A VERIFIED")
    elif pr == "BLOCKED":
        st.error("④ PUF Auth\n\nCHIP B BLOCKED")
    elif pr == "REJECTED":
        st.info("④ PUF Auth\n\nNot Required")
    else:
        st.info("④ PUF Auth\n\nPending")

st.divider()

# ── Agent 1 ──────────────────────────────────────────────────────────────────
if st.button("🤖 Run Agent 1 — Parse Document", use_container_width=True):
    with st.spinner("Agent 1 parsing document via AWS Bedrock..."):
        parsed = parse_document(doc["swift"])
        st.session_state["parsed"] = parsed
        # Clear downstream state when re-parsing
        st.session_state.pop("compliance", None)
        st.session_state["payment_result"] = None
    st.success("Agent 1 Complete")

if "parsed" in st.session_state:
    with st.expander("Agent 1 — Parsed Fields", expanded=False):
        st.json(st.session_state["parsed"])

# ── Agent 2 ──────────────────────────────────────────────────────────────────
if "parsed" in st.session_state:
    if st.button("🔍 Run Agent 2 — Compliance Check", use_container_width=True):
        with st.spinner("Agent 2 running IFSCA compliance rules..."):
            result = check_compliance(
                doc["swift"],
                doc["bill_of_lading"],
                st.session_state["parsed"]
            )
            st.session_state["compliance"] = result
            st.session_state["payment_result"] = None

if "compliance" in st.session_state:
    result = st.session_state["compliance"]
    with st.expander("Agent 2 — Compliance Result", expanded=True):
        if result["status"] == "CLEARED":
            st.success(f"✅ Status: {result['status']}")
        elif result["status"] == "FLAGGED":
            st.warning(f"⚠️ Status: {result['status']}")
        else:
            st.error(f"❌ Status: {result['status']}")
        for issue in result["issues"]:
            st.write(f"→ {issue}")
        st.info(result["compliance_memo"])

# ── Human-in-the-loop + PUF Auth ─────────────────────────────────────────────
if "compliance" in st.session_state:
    compliance_status = st.session_state["compliance"]["status"]
    st.divider()

    if compliance_status == "REJECTED":
        st.subheader("🚫 Transaction Blocked by Compliance")
        st.error(
            "Critical compliance issues detected. "
            "This transaction cannot proceed to human approval or PUF signing."
        )
        st.info("Human Approval: NOT EXECUTED | PUF Authentication: NOT EXECUTED")

    else:
        st.subheader("👤 Human-in-the-Loop Approval")

        if compliance_status == "FLAGGED":
            st.warning(
                "⚠️ This transaction was FLAGGED for manual review. "
                "Officer must review the issues above before approving."
            )
        else:
            st.warning("Officer approval required before PUF signing.")

        officer_note = st.text_input(
            "Officer Note",
            placeholder="e.g. Verified goods manifest manually"
        )

        col_approve, col_reject = st.columns(2)

        with col_approve:
            if st.button("✅ Approve & Sign with PUF", use_container_width=True):
                tx_string = (
                    f"APPROVE LC {doc['swift']['doc_id']} | "
                    f"USD {doc['swift']['amount_usd']} | "
                    f"{officer_note}"
                )
                auth = sign_transaction(tx_string, chip=chip)
                verified = verify_transaction(tx_string, auth["signature"], auth["public_key"])

                if chip == "A" and verified:
                    st.session_state["payment_result"] = "APPROVED"
                    st.success("✅ PUF Authentication: APPROVED")
                    st.code(f"Signature: {auth['signature'][:60]}...")
                    st.caption("🔐 Key generated from silicon — never stored in memory")
                else:
                    st.session_state["payment_result"] = "BLOCKED"
                    st.error("❌ Cloned device detected — Transaction BLOCKED")
                    st.caption(
                        "Chip B signature rejected by Chip A public key registry. "
                        "Different silicon produces a different key — the signature is invalid."
                    )

        with col_reject:
            if st.button("❌ Reject Transaction", use_container_width=True):
                st.session_state["payment_result"] = "REJECTED"
                st.error("Transaction rejected by officer.")

# ── Final result banner ───────────────────────────────────────────────────────
pr = st.session_state["payment_result"]
if pr == "APPROVED":
    st.divider()
    st.success(
        f"✅ PAYMENT RELEASED — LC {doc['swift']['doc_id']} | "
        f"USD {doc['swift']['amount_usd']:,.2f} | "
        f"Authenticated via Chip A PUF"
    )
elif pr == "BLOCKED":
    st.divider()
    st.error(
        f"🚫 PAYMENT BLOCKED — LC {doc['swift']['doc_id']} | "
        "Device identity does not match enrolled Chip A. Clone attack prevented."
    )

import streamlit as st
import json, sys, os

sys.path.append(os.path.join(os.path.dirname(__file__), "agents"))
from agent1_parser import parse_document
from agent2_compliance import check_compliance
from agent3_puf_auth import sign_transaction, verify_transaction

# Load synthetic docs
with open("synthetic_docs.json") as f:
    docs = json.load(f)

st.set_page_config(page_title="PUF-Pay Trade Finance", page_icon="🔐", layout="wide")

st.title("🔐 PUF-Pay — Secure Trade Finance Platform")
st.caption("GIFT City IBU | Powered by AWS Bedrock + Hardware PUF Authentication")

st.divider()

# Sidebar
st.sidebar.header("Select Transaction")
doc_index = st.sidebar.selectbox("Choose Document", range(10), format_func=lambda i: f"LC-{i+1}: {docs[i]['swift']['applicant'][:20]}")
chip = st.sidebar.radio("Officer Device", ["A", "B"], help="Chip B simulates a cloned/compromised device")

doc = docs[doc_index]

# Show raw document
col1, col2 = st.columns(2)
with col1:
    st.subheader("📄 SWIFT MT700 — Letter of Credit")
    st.json(doc["swift"])
with col2:
    st.subheader("🚢 Bill of Lading")
    st.json(doc["bill_of_lading"])

st.divider()

# Agent 1
if st.button("🤖 Run Agent 1 — Parse Document", use_container_width=True):
    with st.spinner("Agent 1 parsing document via AWS Bedrock..."):
        parsed = parse_document(doc["swift"])
        st.session_state["parsed"] = parsed
    st.success("Agent 1 Complete")
    st.json(parsed)

# Agent 2
if "parsed" in st.session_state:
    if st.button("🔍 Run Agent 2 — Compliance Check", use_container_width=True):
        with st.spinner("Agent 2 running IFSCA compliance rules..."):
            result = check_compliance(doc["swift"], doc["bill_of_lading"], st.session_state["parsed"])
            st.session_state["compliance"] = result

        if result["status"] == "CLEARED":
            st.success(f"✅ Status: {result['status']}")
        elif result["status"] == "FLAGGED":
            st.warning(f"⚠️ Status: {result['status']}")
        else:
            st.error(f"❌ Status: {result['status']}")

        for issue in result["issues"]:
            st.write(f"→ {issue}")
        st.info(result["compliance_memo"])

# Agent 3 — Human in the loop
if "compliance" in st.session_state:
    st.divider()
    st.subheader("👤 Human-in-the-Loop Approval")
    st.warning("Officer approval required before PUF signing.")

    officer_note = st.text_input("Officer Note", placeholder="e.g. Verified goods manifest manually")

    col_approve, col_reject = st.columns(2)

    with col_approve:
        if st.button("✅ Approve & Sign with PUF", use_container_width=True):
            tx_string = f"APPROVE LC {doc['swift']['doc_id']} | USD {doc['swift']['amount_usd']} | {officer_note}"
            auth = sign_transaction(tx_string, chip=chip)
            verified = verify_transaction(tx_string, auth["signature"], auth["public_key"])

            if chip == "A":
                st.success("✅ PUF Authentication: APPROVED")
                st.code(f"Signature: {auth['signature'][:60]}...")
                st.caption("🔐 Key generated from silicon — never stored in memory")
            else:
                st.error("❌ Cloned device detected — Transaction BLOCKED")
                st.caption("Chip B signature rejected by Chip A public key registry")

    with col_reject:
        if st.button("❌ Reject Transaction", use_container_width=True):
            st.error("Transaction rejected by officer.")
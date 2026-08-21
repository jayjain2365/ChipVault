# PUF-Pay — Hardware-Rooted Secure Trade Finance

> **"Your silicon is your password."**

GIFT IFIH Young Builders Program 2026 · Track 1: Agentic AI in Financial Services

---

## The Problem

GIFT City International Banking Units (IBUs) process cross-border Letters of Credit worth millions of dollars daily. Today, three pain points slow every transaction:

| Pain Point | Impact |
|---|---|
| Manual document review | Officers spend 4+ hours per LC checking dates, goods, ports, and amounts by hand |
| Compliance errors | Missed IFSCA rule violations create regulatory risk and payment disputes |
| Software-stored private keys | Officer credentials live in files or databases — one breach exposes every transaction |

The third problem is the most dangerous. If an officer's signing key is stolen, an attacker can authorise fraudulent payments indefinitely. Changing the key requires revoking and re-enrolling across every system.

**PUF-Pay solves all three** with an AI-powered document pipeline and a signing key that physically cannot be stolen — because it doesn't exist until the moment of signing.

---

## The Solution

```
SWIFT MT700 Letter of Credit + Bill of Lading
                    │
                    ▼
   ┌────────────────────────────────────────┐
   │  Agent 1 — AI Document Parsing        │
   │  AWS Bedrock / Claude Sonnet           │
   │  Extracts: parties, amounts, goods,    │
   │  ports, dates, one-line summary        │
   └────────────────────┬───────────────────┘
                        │ structured JSON
                        ▼
   ┌────────────────────────────────────────┐
   │  Agent 2 — IFSCA Compliance Check     │
   │  4 deterministic rules + AI memo       │
   │                                        │
   │  CLEARED ──────────────────────────┐  │
   │  FLAGGED ──── officer review ──┐   │  │
   │  REJECTED ── auto-block ──┐    │   │  │
   └───────────────────────────┼────┼───┼──┘
                                │    │   │
                    BLOCKED ◄───┘    │   │
                                     ▼   ▼
   ┌────────────────────────────────────────┐
   │  Human-in-the-Loop (FLAGGED only)     │
   │  Officer reviews and approves/rejects  │
   └────────────────────┬───────────────────┘
                        │ approved
                        ▼
   ┌────────────────────────────────────────┐
   │  Agent 3 — PUF Authentication         │
   │  Ring Oscillator PUF · ECDSA           │
   │                                        │
   │  Chip A (enrolled) → APPROVED ✅      │
   │  Chip B (clone)    → BLOCKED  🚫      │
   └────────────────────────────────────────┘
                        │
                        ▼
              Signed Transaction
```

---

## What Each Agent Does

**Agent 1 — AI Document Parser**
Calls Claude Sonnet on AWS Bedrock with the raw SWIFT MT700 JSON and asks it to extract every key field: applicant, beneficiary, amount, currency, goods description, port of loading, port of discharge, issue date, expiry date, and a one-line human-readable summary. The output is clean structured JSON that downstream agents and the UI can work with directly. This removes the manual data-entry step that currently takes officers 30–60 minutes per document.

**Agent 2 — IFSCA Compliance Checker**
Runs four deterministic rule checks against the parsed document and its paired Bill of Lading: expiry date before issue date, goods mismatch between LC and BL, amount above the IFSCA reporting threshold (USD 200,000), and port-of-loading mismatch. Any CRITICAL violation auto-rejects the transaction. Threshold flags escalate to human review. After rule evaluation, Agent 2 calls Bedrock again to generate a two-sentence formal compliance memo — the kind an IFSCA examiner would write — explaining the decision in plain language.

**Agent 3 — PUF Authentication**
After compliance passes and (if flagged) an officer approves, Agent 3 signs the transaction using a key derived from the officer's hardware chip. The chip uses a Ring Oscillator PUF — 256 tiny oscillating circuits whose frequencies are unique to that chip's silicon — to regenerate a 128-bit key. SHA-256 expands this to a 256-bit ECDSA private key, which signs the transaction string. The bank verifies the signature against the enrolled Chip A public key. A cloned device has different silicon, produces a different key, and its signature fails — the clone is detected and blocked automatically.

---

## What is a PUF? (No hardware jargon)

Think of a silicon chip like a fingerprint. Even two chips made from identical blueprints on the same factory line come out microscopically different — tiny variations in how fast electrons flow through each transistor. These differences are random, permanent, and impossible to copy.

A **Physical Unclonable Function (PUF)** turns those silicon quirks into a key. Instead of storing a private key in memory (where it can be stolen), the chip *generates* the key fresh each time it is needed, from its own physical properties, then discards it immediately after signing.

**What this means for a bank:** Even if an attacker steals the officer's laptop, installs malware, or physically clones the chip, the clone cannot produce the same key. The silicon is different. The signature fails. The payment is blocked.

In PUF-Pay, we simulate this in software using per-chip seed values that mimic manufacturing variation. The cryptographic flow — key derivation, signing, and verification — is identical to what runs on real Xilinx Artix-7 hardware.

---

## Architecture Layers

| Layer | Technology | What it does |
|---|---|---|
| Hardware PUF | Verilog-2001 · Vivado XSim · Artix-7 | 256 Ring Oscillators → 128-bit unique key |
| Fuzzy Extractor | RTL module (`rtl/fuzzy_extractor.v`) | Corrects 1-bit noise per byte to stabilise key |
| Key Expansion | SHA-256 | 128-bit PUF key → 256-bit ECDSA private key |
| ECDSA Signing | Python `ecdsa` · SECP256k1 | Signs transaction string; bank verifies |
| Agent 1 | AWS Bedrock · Claude Sonnet | AI document parsing |
| Agent 2 | AWS Bedrock · Claude Sonnet | IFSCA compliance + AI memo |
| UI | Streamlit | Dark fintech dashboard, live pipeline status |

---

## Tech Stack

| Component | Version |
|---|---|
| Python | 3.10+ |
| streamlit | 1.40+ |
| boto3 | 1.35+ |
| ecdsa | 0.19+ |
| faker | 33+ |
| AWS Bedrock model | `us.anthropic.claude-sonnet-4-6` (us-east-1) |

---

## Repository Structure

```
ChipVault/
├── agents/
│   ├── agent1_parser.py        # AWS Bedrock document parser
│   ├── agent2_compliance.py    # IFSCA compliance checker + AI memo
│   └── agent3_puf_auth.py      # PUF-based ECDSA signing & verification
│
├── rtl/                        # Synthesisable Verilog (hardware PUF)
│   ├── ring_oscillator.v
│   ├── frequency_counter.v
│   ├── ro_puf_core.v
│   ├── fuzzy_extractor.v
│   ├── anti_tamper.v
│   └── puf_pay_top.v
│
├── tb/
│   └── tb_two_chips.v          # Vivado testbench — generates Chip A + B keys
│
├── app.py                      # Streamlit UI (main demo)
├── generate_data.py            # Synthetic LC + BL document generator
├── test_all.py                 # Full pipeline test suite (6 tests)
├── synthetic_docs.json         # 10 pre-generated document pairs
├── puf_key_chipA.txt           # Chip A PUF key (from Vivado simulation)
├── puf_key_chipB.txt           # Chip B PUF key (different silicon)
└── requirements.txt
```

---

## Quickstart

**Prerequisites:** Python 3.10+, an AWS account with Bedrock enabled (us-east-1, Claude Sonnet model access required), AWS credentials configured.

```bash
git clone https://github.com/jayjain2365/ChipVault.git
cd ChipVault
pip install -r requirements.txt
aws configure          # enter Access Key, Secret Key, region: us-east-1
streamlit run app.py
```

Open **http://localhost:8501**

**To run the test suite:**
```bash
python test_all.py
```

---

## Demo Walkthrough

1. Select a transaction from the sidebar (LC-1 through LC-10)
2. Select Officer Device: **A** (trusted chip) or **B** (clone attack demo)
3. The pipeline runs automatically — no button clicks needed
4. Watch the four pipeline stages complete in real time

**Scenarios to demo:**

| Transaction | What to expect |
|---|---|
| LC-1, LC-6, LC-10 | CLEARED → PUF signs automatically → APPROVED |
| LC-2, LC-4, LC-7, LC-9 | FLAGGED → officer must approve → then PUF signs |
| LC-3 | REJECTED — expiry date before issue date |
| LC-5 | REJECTED — goods description mismatch |
| LC-8 | REJECTED — port of loading mismatch |
| Any CLEARED doc + Chip B | BLOCKED — silicon clone attack detected |

---

## Honest Disclosure

We believe transparency matters more than hype. Here is exactly what is simulated vs. real in this prototype:

| Claim | Reality |
|---|---|
| Ring Oscillator PUF (256 ROs, 128-bit response) | Fully implemented in Verilog, functional in Vivado XSim |
| Fuzzy extractor noise correction | Implemented — simplified 1-bit-per-block prototype |
| Anti-tamper monitor | Implemented for voltage, temperature, brute-force |
| Physical silicon entropy | **Simulated** — `CHIP_SEED` parameter mimics manufacturing variation; real entropy comes from actual silicon and cannot be reproduced in RTL simulation |
| Hardware-to-software key bridge | **Simulated** — key written to `.txt` file by testbench; production would use a secure hardware bus or HSM interface |
| SWIFT MT700 documents | **Synthetic** — generated with Faker; not real banking documents |
| IFSCA compliance rules | **Simplified** — 4 rule approximations; real IFSCA compliance is significantly more complex |

---

## Team

**Jay Jain** — Electronics & Communication Engineering (Final Year)  
RTL/VLSI design, Verilog, Vivado, AWS Bedrock integration, Streamlit UI

**Siddharth Pandey** — Co-developer

---

*GIFT IFIH Young Builders Program 2026 · Track 1: Agentic AI in Financial Services*

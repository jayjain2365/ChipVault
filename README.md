# 🔐 PUF-Pay — Hardware-Rooted Secure Trade Finance

**GIFT IFIH Young Builders Program 2026**

> *"Your silicon is your password."*

A secure trade finance platform that combines AI document processing, IFSCA compliance automation, and hardware-rooted payment authentication using Physical Unclonable Functions (PUF).

---

## The Problem

GIFT City IBUs process cross-border trade finance (Letters of Credit, Bills of Lading). Current pain points:

| Pain Point | Impact |
|---|---|
| Manual LC review | 4+ hours per transaction |
| Compliance errors | Regulatory risk under IFSCA |
| Software-stored private keys | Vulnerable to theft, malware, SIM swap |
| No hardware-rooted officer identity | Cannot detect cloned/compromised devices |

---

## The Solution

PUF-Pay solves all three with a **3-agent AI pipeline + hardware PUF authentication layer**:

```
SWIFT MT700 + Bill of Lading
          │
          ▼
  ① Agent 1 — AI Document Parsing (AWS Bedrock)
          │
          ▼
  ② Agent 2 — IFSCA Compliance Check
          │
     ┌────┴────┐
  REJECTED   CLEARED / FLAGGED
     │              │
  BLOCKED      ③ Human Approval
                    │
                    ▼
            ④ PUF Authentication
               ┌────┴────┐
            Chip A      Chip B
           APPROVED    BLOCKED
```

---

## What is a PUF?

Every silicon chip has microscopic manufacturing variations — tiny differences in transistor speed, wire capacitance, and doping levels. These are random, permanent, and impossible to replicate, even by the original manufacturer.

A **Physical Unclonable Function (PUF)** measures these variations using **256 Ring Oscillators** to generate a unique **128-bit fingerprint** for every chip.

```
Traditional payment auth:          PUF-Pay:
  Private key stored in memory  →    Key regenerated from silicon
  Attacker steals key file      →    No key to steal — it doesn't exist
  Clone chip, copy key          →    Clone has different silicon → different key
```

**Key properties:**
- Key is **never stored** — regenerated on demand, discarded after signing
- Even an identical-model chip produces a **different key** (different silicon)
- A cloned device fails authentication because its oscillator frequencies differ

---

## System Architecture

### Layer 1 — Hardware PUF (Verilog / Vivado)

| Module | File | Function |
|---|---|---|
| Ring Oscillator | `rtl/ring_oscillator.v` | Single odd-stage inverter loop, free-oscillates |
| Frequency Counter | `rtl/frequency_counter.v` | Counts RO edges in fixed clock window (CDC-safe) |
| RO PUF Core | `rtl/ro_puf_core.v` | 256 ROs → pairwise comparison → 128-bit response |
| Fuzzy Extractor | `rtl/fuzzy_extractor.v` | Corrects 1-bit noise per 8-bit block, stabilises key |
| Anti-Tamper | `rtl/anti_tamper.v` | Detects voltage/temperature attack, zeroizes on breach |
| Top Integration | `rtl/puf_pay_top.v` | Full system with `CHIP_SEED` parameter for per-chip ID |

The Vivado testbench (`tb/tb_two_chips.v`) runs the RTL simulation for two chips and writes their derived keys to `puf_key_chipA.txt` and `puf_key_chipB.txt`.

### Layer 2 — AI Document Processing (AWS Bedrock)

**Agent 1** (`agents/agent1_parser.py`): Calls Claude Sonnet on AWS Bedrock to parse a SWIFT MT700 Letter of Credit JSON. Extracts: applicant, beneficiary, amount, currency, goods, ports, dates, and a one-line summary. Returns clean structured JSON.

**Agent 2** (`agents/agent2_compliance.py`): Runs 4 deterministic IFSCA compliance rules, then calls Bedrock to generate a formal compliance memo.

### Layer 3 — IFSCA Compliance Rules

| Rule | Trigger | Severity |
|---|---|---|
| Expiry before issue date | `expiry_date < issue_date` | CRITICAL → REJECTED |
| Goods mismatch | LC goods ≠ Bill of Lading goods | CRITICAL → REJECTED |
| Amount threshold | `amount > USD 200,000` | FLAG → FLAGGED |
| Port mismatch | LC port ≠ BL port of loading | CRITICAL → REJECTED |

**Decision logic:** Any CRITICAL issue → `REJECTED`. Non-critical only → `FLAGGED`. No issues → `CLEARED`.

### Layer 4 — Human-in-the-Loop

Officer reviews parsed document and compliance result. Can approve or reject. Required before PUF signing. REJECTED transactions (by compliance engine) cannot reach this stage.

### Layer 5 — PUF Authentication (ECDSA)

```
Chip regenerates 128-bit key from silicon
        │
        ▼
SHA-256 key expansion → 256-bit ECDSA private key (SECP256k1)
        │
        ▼
Signs transaction string
        │
        ▼
Bank verifies: valid sig from enrolled Chip A public key?
        │
   ┌────┴────┐
  Yes        No
APPROVED   BLOCKED (different silicon = different key = invalid sig)
```

---

## Repository Structure

```
ChipVault/
├── agents/
│   ├── agent1_parser.py       # AWS Bedrock document parser
│   ├── agent2_compliance.py   # IFSCA compliance checker
│   └── agent3_puf_auth.py     # PUF-based ECDSA signing
│
├── rtl/                       # Synthesizable Verilog (hardware PUF)
│   ├── ring_oscillator.v
│   ├── frequency_counter.v
│   ├── ro_puf_core.v
│   ├── fuzzy_extractor.v
│   ├── anti_tamper.v
│   └── puf_pay_top.v
│
├── tb/                        # Vivado testbenches
│   └── tb_two_chips.v         # Generates Chip A + Chip B keys
│
├── app.py                     # Streamlit UI (main demo)
├── generate_data.py           # Synthetic LC + BL generator
├── synthetic_docs.json        # 10 pre-generated document pairs
├── puf_key_chipA.txt          # Chip A PUF-derived key (from Vivado)
├── puf_key_chipB.txt          # Chip B PUF-derived key (from Vivado)
├── requirements.txt
└── README.md
```

---

## Quickstart

### Prerequisites
- Python 3.10+
- AWS account with Bedrock access (us-east-1, Claude Sonnet model enabled)
- AWS credentials configured

### Setup

```bash
git clone <repo>
cd ChipVault
pip install -r requirements.txt
aws configure          # enter your Access Key, Secret, region: us-east-1
streamlit run app.py
```

Open **http://localhost:8501**

### Running a Demo

1. Select a transaction from the sidebar (LC-1 through LC-10)
2. Select Officer Device: **A** (trusted) or **B** (clone attack demo)
3. Click **Run Agent 1** — parses the LC via Bedrock
4. Click **Run Agent 2** — checks compliance
5. If CLEARED or FLAGGED: enter an officer note and click **Approve & Sign**
6. Watch PUF authentication pass (Chip A) or fail (Chip B)

**Demo cheat sheet:**

| Scenario | Transaction |
|---|---|
| Happy path (CLEARED → approved) | LC-1, LC-6, or LC-10 |
| Flagged for manual review | LC-2, LC-4, LC-7, or LC-9 |
| Expiry date CRITICAL | LC-3 |
| Goods mismatch CRITICAL | LC-5 |
| Port mismatch CRITICAL | LC-8 |
| Clone attack demo | Any CLEARED doc + select Chip B |

---

## Honest Disclosure (Modeling Notes)

We believe in being transparent about what is real vs. simulated in this prototype:

| Claim | Reality |
|---|---|
| Ring Oscillator PUF | ✅ Fully implemented in Verilog, verified in Vivado XSim |
| 256 ROs → 128-bit response | ✅ Implemented and tested |
| Fuzzy extractor (noise correction) | ✅ Simplified 1-bit-per-block correction — functional prototype |
| Anti-tamper monitor | ✅ Implemented for voltage, temperature, brute-force scenarios |
| Physical silicon entropy | ⚠️ Simulated via `CHIP_SEED` parameter — real silicon entropy comes from manufacturing variation, which cannot be modelled in RTL simulation |
| Hardware ↔ software bridge | ⚠️ Key written to a `.txt` file by Vivado testbench, read by Python — in production this would be a secure hardware bus |
| SWIFT documents | ⚠️ Synthetic data generated with Faker — not real banking documents |
| IFSCA compliance rules | ⚠️ 4 simplified rules — real IFSCA compliance is significantly more complex |

---

## Tech Stack

| Component | Technology |
|---|---|
| Hardware PUF | Verilog-2001, Xilinx Vivado 2025.1, Artix-7 |
| AI parsing | AWS Bedrock, Claude Sonnet (`us.anthropic.claude-sonnet-4-6`) |
| Compliance memo | AWS Bedrock, Claude Sonnet |
| Cryptography | Python `ecdsa` library, SECP256k1 curve |
| Key expansion | SHA-256 (128-bit PUF → 256-bit ECDSA private key) |
| UI | Streamlit |
| AWS SDK | boto3 |

---

## Team

**Jay Jain** — Electronics & Communication Engineering (Final Year) · RTL/VLSI + AWS Integration  
**Siddharth Pandey** — Co-developer

---

*GIFT IFIH Young Builders Program 2026 · Track 1: Agentic AI in Financial Services*

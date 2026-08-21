import json, random, uuid
from faker import Faker
from datetime import datetime, timedelta, date

fake = Faker()
random.seed(42)

PORTS_LOADING = ["Mundra", "JNPT", "Chennai"]
PORTS_DISCHARGE = ["Singapore", "Dubai", "Rotterdam"]
BANKS = ["DBS GIFT IBU", "HDFC GIFT Branch", "ICICI GIFT IBU"]
GOODS_OPTIONS = [
    "Electronic Components - 500 units",
    "Pharmaceutical Raw Materials - 2000 kg",
    "Textile Machinery Parts - 50 units",
]

ANOMALY_NOTES = {
    "expiry_date":    "EXPIRY DATE BEFORE ISSUE DATE",
    "goods_mismatch": "GOODS MISMATCH WITH BILL OF LADING",
    "port_mismatch":  "PORT OF LOADING MISMATCH BETWEEN LC AND BL",
}


def make_doc_pair(anomaly_type=None, amount=None):
    """
    anomaly_type: None | 'expiry_date' | 'goods_mismatch' | 'port_mismatch'
    amount: fixed USD amount; random if None
    """
    if amount is None:
        amount = round(random.uniform(50000, 180000), 2)

    port_loading = random.choice(PORTS_LOADING)
    port_discharge = random.choice(PORTS_DISCHARGE)
    goods = random.choice(GOODS_OPTIONS)
    today = date.today()

    # Dates
    if anomaly_type == "expiry_date":
        issue_date = (today - timedelta(days=10)).isoformat()
        expiry_date = (today - timedelta(days=30)).isoformat()   # clearly before issue
    else:
        issue_date = fake.date_between("-30d", "today").isoformat()
        expiry_date = fake.date_between("+30d", "+90d").isoformat()

    # BL port — differs from LC only on port_mismatch anomaly
    if anomaly_type == "port_mismatch":
        other_ports = [p for p in PORTS_LOADING if p != port_loading]
        bl_port_loading = random.choice(other_ports)
    else:
        bl_port_loading = port_loading

    goods_match = anomaly_type != "goods_mismatch"

    swift = {
        "doc_type": "SWIFT_MT700",
        "doc_id": str(uuid.uuid4())[:8].upper(),
        "issue_date": issue_date,
        "expiry_date": expiry_date,
        "applicant": fake.company() + " Ltd",
        "beneficiary": fake.company() + " Exports Pvt Ltd",
        "issuing_bank": random.choice(BANKS),
        "amount_usd": amount,
        "currency": "USD",
        "goods_description": goods,
        "port_of_loading": port_loading,
        "port_of_discharge": port_discharge,
        "anomaly_injected": anomaly_type is not None,
        "anomaly_type": anomaly_type or "none",
        "compliance_note": ANOMALY_NOTES.get(anomaly_type, "OK"),
    }

    bl = {
        "doc_type": "BILL_OF_LADING",
        "bl_number": "BL-" + str(uuid.uuid4())[:6].upper(),
        "linked_lc": swift["doc_id"],
        "shipper": swift["beneficiary"],
        "consignee": swift["applicant"],
        "vessel": fake.last_name() + " Star",
        "voyage_no": f"V{random.randint(100, 999)}",
        "port_of_loading": bl_port_loading,
        "port_of_discharge": port_discharge,
        "goods": goods,
        "gross_weight_kg": random.randint(500, 20000),
        "containers": random.randint(1, 10),
        "goods_match": goods_match,
        "bl_date": (datetime.now() - timedelta(days=random.randint(1, 10))).date().isoformat(),
    }

    return {"swift": swift, "bill_of_lading": bl}


# Distribution: 3 CLEARED | 4 FLAGGED | 3 REJECTED
docs = []

# CLEARED — no anomaly, amount < $200k (reporting threshold not triggered)
for _ in range(3):
    docs.append(make_doc_pair(amount=round(random.uniform(50000, 190000), 2)))

# FLAGGED — no anomaly, amount > $200k (IFSCA reporting threshold flag only)
for _ in range(4):
    docs.append(make_doc_pair(amount=round(random.uniform(210000, 500000), 2)))

# REJECTED — one of each CRITICAL anomaly type
docs.append(make_doc_pair(anomaly_type="expiry_date",    amount=round(random.uniform(80000, 400000), 2)))
docs.append(make_doc_pair(anomaly_type="goods_mismatch", amount=round(random.uniform(80000, 400000), 2)))
docs.append(make_doc_pair(anomaly_type="port_mismatch",  amount=round(random.uniform(80000, 400000), 2)))

random.shuffle(docs)

with open("synthetic_docs.json", "w") as f:
    json.dump(docs, f, indent=2)

cleared  = sum(1 for d in docs if not d["swift"]["anomaly_injected"] and d["swift"]["amount_usd"] <= 200000)
flagged  = sum(1 for d in docs if not d["swift"]["anomaly_injected"] and d["swift"]["amount_usd"] > 200000)
rejected = sum(1 for d in docs if d["swift"]["anomaly_injected"])
print(f"Generated 10 document pairs: {cleared} CLEARED | {flagged} FLAGGED | {rejected} REJECTED")
for i, d in enumerate(docs):
    s = d["swift"]
    print(f"  LC-{i+1} ({s['doc_id']}): anomaly={s['anomaly_type']:<16} amount={s['amount_usd']:>10,.0f}")

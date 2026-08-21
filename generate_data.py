import json, random, uuid
from faker import Faker
from datetime import datetime, timedelta

fake = Faker()
random.seed(42)

def make_swift_mt700():
    amount = round(random.uniform(50000, 500000), 2)
    # Inject 1 anomaly in 5 documents
    anomaly = random.random() < 0.2
    return {
        "doc_type": "SWIFT_MT700",
        "doc_id": str(uuid.uuid4())[:8].upper(),
        "issue_date": fake.date_between("-30d", "today").isoformat(),
        "expiry_date": fake.date_between("+30d", "+90d").isoformat(),
        "applicant": fake.company() + " Ltd",
        "beneficiary": fake.company() + " Exports Pvt Ltd",
        "issuing_bank": random.choice(["DBS GIFT IBU", "HDFC GIFT Branch", "ICICI GIFT IBU"]),
        "amount_usd": amount,
        "currency": "USD",
        "goods_description": random.choice([
            "Electronic Components - 500 units",
            "Pharmaceutical Raw Materials - 2000 kg",
            "Textile Machinery Parts - 50 units"
        ]),
        "port_of_loading": random.choice(["Mundra", "JNPT", "Chennai"]),
        "port_of_discharge": random.choice(["Singapore", "Dubai", "Rotterdam"]),
        # Anomaly: expiry before issue date — compliance flag
        "anomaly_injected": anomaly,
        "compliance_note": "EXPIRY BEFORE ISSUE DATE — FLAG" if anomaly else "OK"
    }

def make_bill_of_lading(swift_doc):
    return {
        "doc_type": "BILL_OF_LADING",
        "bl_number": "BL-" + str(uuid.uuid4())[:6].upper(),
        "linked_lc": swift_doc["doc_id"],
        "shipper": swift_doc["beneficiary"],
        "consignee": swift_doc["applicant"],
        "vessel": fake.last_name() + " Star",
        "voyage_no": f"V{random.randint(100,999)}",
        "port_of_loading": swift_doc["port_of_loading"],
        "port_of_discharge": swift_doc["port_of_discharge"],
        "goods": swift_doc["goods_description"],
        "gross_weight_kg": random.randint(500, 20000),
        "containers": random.randint(1, 10),
        # Anomaly: goods mismatch vs LC
        "goods_match": not swift_doc["anomaly_injected"],
        "bl_date": (datetime.now() - timedelta(days=random.randint(1,10))).date().isoformat()
    }

# Generate 10 pairs
docs = []
for i in range(10):
    swift = make_swift_mt700()
    bl = make_bill_of_lading(swift)
    docs.append({"swift": swift, "bill_of_lading": bl})

with open("synthetic_docs.json", "w") as f:
    json.dump(docs, f, indent=2)

print(f"Generated 10 document pairs.")
print(f"Anomalies injected: {sum(1 for d in docs if d['swift']['anomaly_injected'])}")
print("Saved to synthetic_docs.json")
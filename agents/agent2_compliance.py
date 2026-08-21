import boto3, json
import sys, os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent1_parser import parse_document
client = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = "us.anthropic.claude-sonnet-4-6"

def check_compliance(swift: dict, bl: dict, parsed: dict) -> dict:
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

    # Get AI explanation
    prompt = f"""You are a GIFT City IFSCA compliance officer.
    
A trade finance document has been checked. Result: {status}
Issues found: {issues if issues else 'None'}
Transaction: {parsed['summary']}

Write a 2-line compliance decision memo. Be formal and concise."""

    response = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "messages": [{"role": "user", "content": prompt}]
        })
    )
    result = json.loads(response["body"].read())
    memo = result["content"][0]["text"]

    return {
        "status": status,
        "issues": issues,
        "compliance_memo": memo
    }


if __name__ == "__main__":
    with open("synthetic_docs.json") as f:
        docs = json.load(f)

    print("Testing Agent 2 on all 10 documents...\n")
    for i, doc in enumerate(docs):
        parsed = parse_document(doc["swift"])
        result = check_compliance(doc["swift"], doc["bill_of_lading"], parsed)
        print(f"Doc {i+1}: {result['status']}")
        if result['issues']:
            for issue in result['issues']:
                print(f"  → {issue}")
        print(f"  Memo: {result['compliance_memo'][:100]}...")
        print()
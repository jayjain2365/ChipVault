import boto3, json

client = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = "us.anthropic.claude-sonnet-4-6"

def parse_document(doc: dict) -> dict:
    prompt = f"""You are a trade finance document parser for GIFT City IBUs.
    
Analyze this SWIFT MT700 Letter of Credit and extract key fields.
Reply ONLY in JSON with these keys:
- applicant
- beneficiary
- amount_usd
- currency
- goods
- port_of_loading
- port_of_discharge
- issue_date
- expiry_date
- summary (one line description)

Document:
{json.dumps(doc, indent=2)}"""

    response = client.invoke_model(
        modelId=MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 500,
            "messages": [{"role": "user", "content": prompt}]
        })
    )

    result = json.loads(response["body"].read())
    text = result["content"][0]["text"]
    
    # Strip markdown if present
    text = text.replace("```json", "").replace("```", "").strip()
# Extract only the JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    return json.loads(text[start:end])


# Test it
if __name__ == "__main__":
    with open("synthetic_docs.json") as f:
        docs = json.load(f)
    
    print("Testing Agent 1 on first document...\n")
    parsed = parse_document(docs[0]["swift"])
    print(json.dumps(parsed, indent=2))
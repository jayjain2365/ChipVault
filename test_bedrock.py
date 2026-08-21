import boto3, json

client = boto3.client("bedrock-runtime", region_name="us-east-1")

response = client.invoke_model(
    modelId="us.anthropic.claude-sonnet-4-6",
    contentType="application/json",
    accept="application/json",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 20,
        "messages": [{"role": "user", "content": "Reply with exactly: BEDROCK_CONNECTED"}]
    })
)

result = json.loads(response["body"].read())
print(result["content"][0]["text"])
from ecdsa import SigningKey, SECP256k1
import hashlib

# Read PUF key from file
with open(r"C:\Users\jayja\OneDrive\Desktop\PUF\PUF - HACKATHON\shared\puf_key.txt", "r") as f:
    key_hex = f.read().strip()

print("PUF Private Key (hex):", key_hex)

# Convert hex to bytes
key_bytes = bytes.fromhex(key_hex)

# Expand 128-bit key to 256-bit using SHA256 (for SECP256k1 compatibility)
private_key_hash = hashlib.sha256(key_bytes).digest()

# Create ECDSA private key
sk = SigningKey.from_string(private_key_hash, curve=SECP256k1)
vk = sk.verifying_key

# Example transaction
transaction = "PAY 500 TO MERCHANT_X"
print("Transaction:", transaction)

# Sign transaction
signature = sk.sign(transaction.encode())
print("Signature:", signature.hex())

# Verify signature (simulates bank checking it)
if vk.verify(signature, transaction.encode()):
    print("✅ Bank Verification: APPROVED")
else:
    print("❌ Bank Verification: REJECTED")
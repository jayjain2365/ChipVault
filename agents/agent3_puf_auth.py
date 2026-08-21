from ecdsa import SigningKey, SECP256k1
import hashlib, os

# Path to PUF key files (relative to project root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHIP_A_KEY = os.path.join(BASE_DIR, "puf_key_chipA.txt")
CHIP_B_KEY = os.path.join(BASE_DIR, "puf_key_chipB.txt")

def sign_transaction(transaction: str, chip: str = "A") -> dict:
    key_file = CHIP_A_KEY if chip == "A" else CHIP_B_KEY

    with open(key_file, "r") as f:
        key_hex = f.read().strip()

    key_bytes = bytes.fromhex(key_hex)
    private_key_hash = hashlib.sha256(key_bytes).digest()

    sk = SigningKey.from_string(private_key_hash, curve=SECP256k1)
    vk = sk.verifying_key

    signature = sk.sign(transaction.encode())

    return {
        "chip": chip,
        "transaction": transaction,
        "signature": signature.hex(),
        "public_key": vk.to_string().hex(),
        "status": "SIGNED"
    }

def verify_transaction(transaction: str, signature_hex: str, public_key_hex: str) -> bool:
    from ecdsa import VerifyingKey, SECP256k1, BadSignatureError
    vk = VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=SECP256k1)
    try:
        vk.verify(bytes.fromhex(signature_hex), transaction.encode())
        return True
    except BadSignatureError:
        return False


if __name__ == "__main__":
    print("=== PUF-Pay Authentication Demo ===\n")

    tx = "PAY USD 337742 TO GIFT CITY IBU — LC REF: TF-001"

    # Chip A signs (legitimate officer)
    print("Chip A signing...")
    result = sign_transaction(tx, chip="A")
    print(f"Signature: {result['signature'][:40]}...")

    # Verify with Chip A public key
    verified = verify_transaction(tx, result["signature"], result["public_key"])
    print(f"Verification: {'✅ APPROVED' if verified else '❌ REJECTED'}\n")

    # Chip B tries to verify with Chip A signature (cloned device attack)
    print("Simulating cloned device attack (Chip B)...")
    result_b = sign_transaction(tx, chip="B")
    attack = verify_transaction(tx, result_b["signature"], result["public_key"])
    print(f"Cloned device: {'✅ APPROVED' if attack else '❌ REJECTED — Clone detected!'}")
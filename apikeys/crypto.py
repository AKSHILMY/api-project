import base64
import hashlib
import hmac
import os

PREFIX = "sk"


def generate_key() -> tuple[str, str, str]:
    token = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    plaintext = f"{PREFIX}_{token}"
    key_prefix = token[:8]
    key_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    return plaintext, key_prefix, key_hash


def hash_key(plaintext_key: str) -> str:
    return hashlib.sha256(plaintext_key.encode()).hexdigest()


def extract_prefix(plaintext_key: str) -> str:
    if not plaintext_key.startswith(f"{PREFIX}_") or len(plaintext_key) < 11:
        raise ValueError("Malformed key")
    return plaintext_key[3:11]


def keys_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)

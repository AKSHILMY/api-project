import base64
import hashlib
import hmac
import os


def generate_key(prefix: str = "sk", environment: str = "", secret: str = "") -> tuple[str, str, str]:
    token = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode()
    if environment:
        plaintext = f"{prefix}_{environment}_{token}"
    else:
        plaintext = f"{prefix}_{token}"
    key_prefix = token[:8]
    key_hash = hash_key(plaintext, secret)
    return plaintext, key_prefix, key_hash


def hash_key(plaintext_key: str, secret: str) -> str:
    return hmac.new(secret.encode(), plaintext_key.encode(), hashlib.sha256).hexdigest()


_TOKEN_LEN = 43  # len(base64url(32 random bytes)) without padding


def extract_prefix(plaintext_key: str) -> str:
    # Token is always _TOKEN_LEN chars; key_prefix is its first 8 chars.
    # Format: {prefix}_{token}  or  {prefix}_{env}_{token}
    if len(plaintext_key) < _TOKEN_LEN + 2:  # at minimum "x_<token>"
        raise ValueError("Malformed key")
    if plaintext_key[-(  _TOKEN_LEN + 1)] != "_":
        raise ValueError("Malformed key")
    token = plaintext_key[-_TOKEN_LEN:]
    if len(token) < 8:
        raise ValueError("Malformed key")
    return token[:8]


def keys_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)

"""Authentication primitives and intentionally conservative authorization policy."""

import hashlib
import hmac
import secrets

ROLES = (
    "owner",
    "admin",
    "super_admin",
    "pastor",
    "zone_leader",
    "zone_administrator",
    "cell_leader",
    "ministry_leader",
    "cell_director",
    "zone_director",
    "tele_pastor",
    "tele_minister",
)
ADMINS = frozenset({"owner", "admin", "super_admin"})
MEMBER_READERS = ADMINS | {"pastor"}
ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, count, salt, expected = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(count))
        return hmac.compare_digest(actual.hex(), expected)
    except (ValueError, TypeError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

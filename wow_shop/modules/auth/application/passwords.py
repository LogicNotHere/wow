from __future__ import annotations

import hmac
import hashlib
import secrets

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 390000
SALT_SIZE_BYTES = 16


def hash_password(password: str) -> str:
    salt = secrets.token_hex(SALT_SIZE_BYTES)
    derived_key = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    )
    return (
        f"pbkdf2_{PBKDF2_ALGORITHM}"
        f"${PBKDF2_ITERATIONS}"
        f"${salt}"
        f"${derived_key.hex()}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    parts = password_hash.split("$")
    if len(parts) != 4:
        return False

    scheme, raw_iterations, salt, expected_hex = parts
    if scheme != f"pbkdf2_{PBKDF2_ALGORITHM}":
        return False

    try:
        iterations = int(raw_iterations)
    except ValueError:
        return False

    calculated_key = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        iterations,
    )
    return hmac.compare_digest(calculated_key.hex(), expected_hex)

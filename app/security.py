import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from . import config


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, config.PBKDF2_ITERATIONS)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split("$")
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), bytes.fromhex(salt_hex), config.PBKDF2_ITERATIONS
    )
    return hmac.compare_digest(digest.hex(), digest_hex)


def create_token(user_id: int) -> tuple[str, int]:
    expires = datetime.now(timezone.utc) + timedelta(minutes=config.TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expires, "jti": uuid.uuid4().hex}
    token = jwt.encode(payload, config.SECRET_KEY, algorithm=config.ALGORITHM)
    return token, config.TOKEN_EXPIRE_MINUTES * 60


def decode_token(token: str) -> dict:
    return jwt.decode(
        token,
        config.SECRET_KEY,
        algorithms=[config.ALGORITHM],
        options={"require": ["exp", "sub", "jti"]},
    )

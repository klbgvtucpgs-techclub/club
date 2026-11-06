import hashlib
import hmac
import secrets
from datetime import timedelta
from typing import Optional

import bcrypt
import jwt

from .config import settings
from .utils import utcnow


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


# Used to keep login timing similar when the username does not exist.
DUMMY_HASH = hash_password("not-a-real-password")


def create_token(sub: str, role: str, ttl: timedelta) -> str:
    now = utcnow()
    return jwt.encode({"sub": sub, "role": role, "iat": now, "exp": now + ttl}, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None


def generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_otp(email: str, purpose: str, otp: str) -> str:
    return hmac.new(settings.secret_key.encode(), f"{purpose}:{email}:{otp}".encode(), hashlib.sha256).hexdigest()


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)

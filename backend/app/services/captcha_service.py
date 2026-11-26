import hashlib
import hmac
import logging
import random
import time
from typing import Optional

import httpx
from fastapi import HTTPException

from ..config import settings

logger = logging.getLogger("vtu.captcha")
URLS = {
    "turnstile": "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    "hcaptcha": "https://hcaptcha.com/siteverify",
    "recaptcha": "https://www.google.com/recaptcha/api/siteverify",
}

# Alphanumeric characters excluding visually ambiguous ones (0, O, 1, I)
CAPTCHA_CHARS = "23456789ABCDEFGHJKLMNPQRSTUVWXYZ"


def generate_captcha() -> dict[str, str]:
    """Generates a random 5-character captcha code and a tamper-proof HMAC-signed token."""
    code = "".join(random.choices(CAPTCHA_CHARS, k=5))
    timestamp = str(int(time.time()))
    salt = "".join(random.choices(CAPTCHA_CHARS, k=6))
    secret = getattr(settings, "secret_key", "vtu-captcha-secret")
    payload = f"{code}:{timestamp}:{salt}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
    token = f"local:{timestamp}:{salt}:{sig}"
    return {"token": token, "code": code}


def verify_captcha(token: Optional[str], ip: str, code: Optional[str] = None) -> None:
    """Verifies either a built-in local captcha challenge or an external provider (turnstile, hcaptcha, recaptcha)."""
    # 1. Built-in local captcha token
    if token and token.startswith("local:"):
        parts = token.split(":")
        if len(parts) != 4:
            raise HTTPException(400, "Invalid captcha token")
        _, timestamp_str, salt, sig = parts
        try:
            ts = int(timestamp_str)
        except ValueError:
            raise HTTPException(400, "Invalid captcha token")
        # 10 minute expiration
        if time.time() - ts > 600 or ts > time.time() + 60:
            raise HTTPException(400, "Captcha code expired. Please refresh and try again.")
        if not code or not code.strip():
            raise HTTPException(400, "Please enter the security verification captcha code")
        cleaned_code = code.strip().upper()
        secret = getattr(settings, "secret_key", "vtu-captcha-secret")
        payload = f"{cleaned_code}:{timestamp_str}:{salt}"
        expected_sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()[:32]
        if not hmac.compare_digest(expected_sig, sig):
            raise HTTPException(400, "Incorrect captcha code. Please try again.")
        return

    # 2. External provider when configured
    if settings.captcha_secret:
        if not token:
            raise HTTPException(400, "Captcha verification required")
        url = URLS.get(settings.captcha_provider)
        if not url:
            raise HTTPException(500, "Captcha provider is misconfigured")
        try:
            r = httpx.post(url, data={"secret": settings.captcha_secret, "response": token, "remoteip": ip}, timeout=10)
            ok = r.status_code == 200 and bool(r.json().get("success"))
        except Exception:
            logger.exception("Captcha verification failed")
            raise HTTPException(503, "Captcha service unavailable. Try again.")
        if not ok:
            raise HTTPException(400, "Captcha verification failed")
        return

    # 3. No captcha configured and no token passed (development mode)
    return

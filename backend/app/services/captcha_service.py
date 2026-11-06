import logging
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


def verify_captcha(token: Optional[str], ip: str) -> None:
    """No-op when CAPTCHA_SECRET is blank (development). Otherwise the token must verify."""
    if not settings.captcha_secret:
        return
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

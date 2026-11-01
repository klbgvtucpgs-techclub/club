import secrets
import threading
import time
from typing import Optional
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import Admin, Student
from .security import decode_token

ADMIN_COOKIE = "admin_session"
STUDENT_COOKIE = "student_session"
CSRF_COOKIE = "csrf_token"


def client_ip(request: Request) -> str:
    if settings.trust_proxy:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------- in-memory rate limiter (use Redis/your host's limiter if you run several instances) ----------
_hits: dict[tuple, deque] = defaultdict(deque)
_lock = threading.Lock()


def rate_limit(name: str, limit: int, window_seconds: int):
    def dependency(request: Request):
        if not settings.rate_limit_enabled:
            return
        key = (name, client_ip(request))
        now = time.monotonic()
        with _lock:
            q = _hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                raise HTTPException(429, "Too many requests. Please try again later.", headers={"Retry-After": str(window_seconds)})
            q.append(now)

    return dependency


# ---------- cookies ----------
def set_cookie(response: Response, name: str, value: str, max_age: int, path: str = "/", httponly: bool = True):
    response.set_cookie(
        name, value, max_age=max_age, path=path, httponly=httponly,
        secure=settings.cookie_secure, samesite=settings.cookie_samesite,
    )


def clear_cookie(response: Response, name: str, path: str = "/"):
    response.delete_cookie(name, path=path, secure=settings.cookie_secure, samesite=settings.cookie_samesite)


def _session(request: Request, cookie: str) -> Optional[dict]:
    token = request.cookies.get(cookie)
    return decode_token(token) if token else None


# ---------- auth dependencies ----------
def require_student(request: Request, db: Session = Depends(get_db)) -> Student:
    data = _session(request, STUDENT_COOKIE)
    if not data or data.get("role") != "student":
        raise HTTPException(401, "Please log in")
    student = db.get(Student, int(data["sub"]))
    if not student or not student.email_verified:
        raise HTTPException(401, "Please log in")
    return student


def require_admin(request: Request, db: Session = Depends(get_db)) -> Admin:
    data = _session(request, ADMIN_COOKIE)
    if not data or data.get("role") != "admin":
        raise HTTPException(401, "Admin login required")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        header = request.headers.get("x-csrf-token", "")
        cookie = request.cookies.get(CSRF_COOKIE, "")
        if not header or not cookie or not secrets.compare_digest(header, cookie):
            raise HTTPException(403, "CSRF token missing or invalid")
    admin = db.get(Admin, int(data["sub"]))
    if not admin or not admin.active:
        raise HTTPException(401, "Admin login required")
    return admin


def require_superadmin(admin: Admin = Depends(require_admin)) -> Admin:
    if admin.role != "superadmin":
        raise HTTPException(403, "Super admin only")
    return admin

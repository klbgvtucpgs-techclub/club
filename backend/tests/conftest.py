import os

os.environ.update(
    DATABASE_URL="sqlite:///./test.db", SECRET_KEY="test-secret-key-test-secret-key-0123456789",
    EMAIL_BACKEND="memory", RATE_LIMIT_ENABLED="false", APP_ENV="test", CAPTCHA_SECRET="",
    SUPABASE_URL="", SUPABASE_SERVICE_KEY="",
)

import re  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Admin  # noqa: E402
from app.scripts.seed import seed_clubs  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services import email_service  # noqa: E402

ADMIN_PASSWORD = "StrongPass123!"


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_clubs(db)
        db.add(Admin(username="admin", password_hash=hash_password(ADMIN_PASSWORD), role="superadmin"))
        db.commit()
    email_service.OUTBOX.clear()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def last_otp() -> str:
    return re.search(r"\b(\d{6})\b", email_service.OUTBOX[-1]["body"]).group(1)


def student_payload(n: int = 1, club: str = "tech") -> dict:
    return {"usn": f"1VT22CS{n:03d}", "full_name": f"Test Student {n}", "email": f"student{n}@college.edu",
            "phone": "9876543210", "branch": "CSE", "joining_year": 2022, "club_slug": club}


def register_student(client, n: int = 1, club: str = "tech"):
    pending = client.post("/api/auth/register", json=student_payload(n, club))
    assert pending.status_code == 200, pending.text
    pid = pending.json()["pending_id"]
    assert client.post("/api/auth/send-otp", json={"purpose": "register", "pending_id": pid}).status_code == 200
    return client.post("/api/auth/verify-otp", json={"pending_id": pid, "otp": last_otp()})


@pytest.fixture
def admin_client(client):
    r = client.post("/api/admin/login", json={"username": "admin", "password": ADMIN_PASSWORD})
    assert r.status_code == 200, r.text
    client.headers["X-CSRF-Token"] = r.json()["csrf_token"]
    return client

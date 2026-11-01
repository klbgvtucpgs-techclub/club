from .conftest import last_otp, register_student, student_payload
from app.services import email_service


def test_full_flow_issues_sequential_unique_ids(client):
    r1 = register_student(client, 1)
    assert r1.status_code == 200, r1.text
    assert r1.json()["membership"]["membership_code"] == "TECH-2022-0001"
    r2 = register_student(client, 2)
    assert r2.json()["membership"]["membership_code"] == "TECH-2022-0002"
    assert register_student(client, 3, "sports").json()["membership"]["membership_code"] == "SPORTS-2022-0001"
    assert any("TECH-2022-0001" in m["body"] for m in email_service.OUTBOX)  # confirmation email


def test_student_can_see_own_ids_after_verification(client):
    register_student(client, 1)
    me = client.get("/api/memberships/me")
    assert me.status_code == 200 and me.json()[0]["membership_code"] == "TECH-2022-0001"


def test_otp_attempt_limit(client):
    pid = client.post("/api/auth/register", json=student_payload(1)).json()["pending_id"]
    client.post("/api/auth/send-otp", json={"purpose": "register", "pending_id": pid})
    good = last_otp()
    wrong = "000000" if good != "000000" else "111111"
    for _ in range(3):
        assert client.post("/api/auth/verify-otp", json={"pending_id": pid, "otp": wrong}).status_code == 400
    assert client.post("/api/auth/verify-otp", json={"pending_id": pid, "otp": good}).status_code == 429


def test_duplicate_membership_rejected(client):
    assert register_student(client, 1).status_code == 200
    assert client.post("/api/auth/register", json=student_payload(1)).status_code == 409


def test_same_student_can_join_second_club(client):
    register_student(client, 1, "tech")
    r = register_student(client, 1, "multimedia")
    assert r.json()["membership"]["membership_code"] == "MM-2022-0001"


def test_validation_errors(client):
    bad = student_payload(1) | {"usn": "BADUSN"}
    assert client.post("/api/auth/register", json=bad).status_code == 422
    bad = student_payload(1) | {"phone": "12345"}
    assert client.post("/api/auth/register", json=bad).status_code == 422


def test_login_otp_flow(client):
    register_student(client, 1)
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401
    client.post("/api/auth/send-otp", json={"purpose": "login", "email": "student1@college.edu"})
    assert client.post("/api/auth/login", json={"email": "student1@college.edu", "otp": last_otp()}).status_code == 200
    assert client.get("/api/auth/me").status_code == 200

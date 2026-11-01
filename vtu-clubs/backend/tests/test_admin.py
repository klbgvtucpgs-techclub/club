import io

from PIL import Image

from .conftest import register_student


def test_admin_routes_require_login(client):
    for path in ("/api/admin/students", "/api/admin/dashboard", "/api/admin/announcements"):
        assert client.get(path).status_code == 401


def test_wrong_password(client):
    assert client.post("/api/admin/login", json={"username": "admin", "password": "nope"}).status_code == 401


def test_student_session_cannot_access_admin(client):
    register_student(client, 1)
    assert client.get("/api/admin/students").status_code == 401


def test_csrf_required_for_writes(admin_client):
    token = admin_client.headers.pop("X-CSRF-Token")
    body = {"title": "Hackathon", "message": "Register now", "club_slug": "tech", "published": True}
    assert admin_client.post("/api/admin/announcements", json=body).status_code == 403
    admin_client.headers["X-CSRF-Token"] = token
    assert admin_client.post("/api/admin/announcements", json=body).status_code == 201


def test_announcement_draft_then_publish(admin_client):
    r = admin_client.post("/api/admin/announcements", json={"title": "Draft one", "message": "x", "published": False})
    ann_id = r.json()["id"]
    assert admin_client.get("/api/announcements").json() == []
    assert admin_client.patch(f"/api/admin/announcements/{ann_id}", json={"published": True}).status_code == 200
    assert len(admin_client.get("/api/announcements").json()) == 1
    # club filter includes global announcements
    assert len(admin_client.get("/api/announcements?club=sports").json()) == 1


def test_photo_upload_and_gallery(admin_client):
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "orange").save(buf, "PNG")
    files = {"file": ("a.png", buf.getvalue(), "image/png")}
    r = admin_client.post("/api/admin/photos", data={"club_slug": "tech", "title": "Opening", "event_name": "Hackathon"}, files=files)
    assert r.status_code == 201, r.text
    gallery = admin_client.get("/api/gallery?club=tech").json()
    assert gallery["total"] == 1 and gallery["items"][0]["event_name"] == "Hackathon"
    assert admin_client.get("/api/gallery?club=sports").json()["total"] == 0
    assert admin_client.delete(f"/api/admin/photos/{r.json()['id']}").status_code == 200


def test_fake_image_rejected(admin_client):
    files = {"file": ("evil.png", b"<script>alert(1)</script>", "image/png")}
    r = admin_client.post("/api/admin/photos", data={"club_slug": "tech", "title": "x"}, files=files)
    assert r.status_code == 400


def test_students_list_search_and_export(admin_client):
    register_student(admin_client, 1)
    register_student(admin_client, 2, "sports")
    res = admin_client.get("/api/admin/students?q=SPORTS-2022").json()
    assert res["total"] == 1 and res["items"][0]["usn"] == "1VT22CS002"
    csv_text = admin_client.get("/api/admin/students/export").text
    assert "TECH-2022-0001" in csv_text and "SPORTS-2022-0001" in csv_text


def test_registration_link_lifecycle(admin_client):
    r = admin_client.post("/api/admin/registration-links", json={"club_slug": "tech", "title": "Tech drive"})
    assert r.status_code == 201
    token, link_id = r.json()["public_token"], r.json()["id"]
    assert admin_client.get(f"/api/registration-links/{token}").status_code == 200
    admin_client.patch(f"/api/admin/registration-links/{link_id}", json={"active": False})
    assert admin_client.get(f"/api/registration-links/{token}").status_code == 403


def test_dashboard_counts(admin_client):
    register_student(admin_client, 1)
    d = admin_client.get("/api/admin/dashboard").json()
    assert d["total_students"] == 1
    assert {c["slug"]: c["members"] for c in d["members_per_club"]}["tech"] == 1

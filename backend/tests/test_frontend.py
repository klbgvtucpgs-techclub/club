def test_frontend_is_served_by_the_backend(client):
    r = client.get("/")
    assert r.status_code == 200 and "VTU Clubs" in r.text
    assert client.get("/assets/images/logo.png").status_code == 200
    assert client.get("/api/health").json() == {"status": "ok"}

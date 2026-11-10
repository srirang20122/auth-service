from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
USER = {"full_name": "Test User", "email": "Test@Example.com", "password": "s3cret-pass"}


def login():
    r = client.post("/auth/login", json={"email": USER["email"], "password": USER["password"]})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_full_flow():
    r = client.post("/auth/register", json=USER)
    assert r.status_code == 201, r.text
    assert r.json()["email"] == "test@example.com"

    assert client.post("/auth/register", json=USER).status_code == 409

    bad = client.post("/auth/login", json={"email": USER["email"], "password": "wrong-pass"})
    assert bad.status_code == 401

    token = login()
    me = client.get("/auth/me", headers=auth(token))
    assert me.status_code == 200
    assert me.json()["full_name"] == "Test User"

    assert client.post("/auth/logout", headers=auth(token)).status_code == 204
    assert client.get("/auth/me", headers=auth(token)).status_code == 401

    assert client.get("/auth/me", headers=auth(login())).status_code == 200


def test_requires_token():
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=auth("not-a-jwt")).status_code == 401


def test_validation():
    r = client.post("/auth/register", json={"full_name": "A", "email": "bad", "password": "x"})
    assert r.status_code == 422


def test_metrics_exposed():
    body = client.get("/metrics").text
    assert 'auth_login_total{result="success"}' in body
    assert 'auth_login_total{result="failed"}' in body
    assert 'auth_register_total{result="duplicate"}' in body
    assert "auth_logout_total" in body
    assert "http_request_duration_seconds_bucket" in body

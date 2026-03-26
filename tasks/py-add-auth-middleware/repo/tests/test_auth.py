import jwt
import pytest
from app import app

SECRET_KEY = "test-secret"


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def make_token(payload=None, key=SECRET_KEY):
    return jwt.encode(payload or {"user": "alice"}, key, algorithm="HS256")


def test_no_auth_header_returns_401(client):
    resp = client.get("/data")
    assert resp.status_code == 401


def test_invalid_token_returns_403(client):
    resp = client.get("/data", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 403


def test_valid_token_returns_200(client):
    token = make_token()
    resp = client.get("/data", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json["items"] == ["a", "b", "c"]


def test_wrong_secret_returns_403(client):
    token = make_token(key="wrong-secret")
    resp = client.get("/data", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403

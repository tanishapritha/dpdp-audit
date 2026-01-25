import pytest
from fastapi.testclient import TestClient

def test_login_success(client: TestClient, test_user):
    login_data = {
        "username": "test_tester@example.com",
        "password": "testpassword",
    }
    response = client.post("/api/v1/login/access-token", data=login_data)
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_wrong_password(client: TestClient, test_user):
    login_data = {
        "username": "test_tester@example.com",
        "password": "wrongpassword",
    }
    response = client.post("/api/v1/login/access-token", data=login_data)
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect email or password"

def test_login_nonexistent_user(client: TestClient):
    login_data = {
        "username": "ghost@example.com",
        "password": "somepassword",
    }
    response = client.post("/api/v1/login/access-token", data=login_data)
    assert response.status_code == 400

def test_get_me_authorized(client: TestClient, user_token_headers):
    response = client.get("/api/v1/me", headers=user_token_headers)
    assert response.status_code == 200
    assert response.json()["email"] == "test_tester@example.com"

def test_get_me_unauthorized(client: TestClient):
    response = client.get("/api/v1/me")
    assert response.status_code == 401 # FastAPI OAuth2 mismatch

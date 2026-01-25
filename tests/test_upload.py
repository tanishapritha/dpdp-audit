import pytest
from fastapi.testclient import TestClient
import io

def test_upload_pdf_success(client: TestClient, user_token_headers):
    file_content = b"%PDF-1.4 test content"
    file = io.BytesIO(file_content)
    response = client.post(
        "/api/v1/upload",
        headers=user_token_headers,
        files={"file": ("test.pdf", file, "application/pdf")}
    )
    assert response.status_code == 201
    assert "policy_id" in response.json()
    assert response.json()["filename"] == "test.pdf"

def test_upload_non_pdf_fails(client: TestClient, user_token_headers):
    file_content = b"plain text content"
    file = io.BytesIO(file_content)
    response = client.post(
        "/api/v1/upload",
        headers=user_token_headers,
        files={"file": ("test.txt", file, "text/plain")}
    )
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]

def test_upload_unauthorized(client: TestClient):
    file_content = b"%PDF-1.4 test content"
    file = io.BytesIO(file_content)
    response = client.post(
        "/api/v1/upload",
        files={"file": ("test.pdf", file, "application/pdf")}
    )
    assert response.status_code == 401

def test_get_status_nonexistent(client: TestClient, user_token_headers):
    response = client.get(
        "/api/v1/non-existent-uuid/status",
        headers=user_token_headers
    )
    assert response.status_code == 404

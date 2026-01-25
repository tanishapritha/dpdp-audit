import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import io
import time

# Mocking background task to keep tests synchronous and predictable
def test_full_audit_flow_success(client: TestClient, user_token_headers):
    # 1. Upload
    file_content = b"%PDF-1.4 test content"
    file = io.BytesIO(file_content)
    
    with patch("app.api.v1.endpoints.upload.process_policy_task") as mock_task:
        response = client.post(
            "/api/v1/upload",
            headers=user_token_headers,
            files={"file": ("test.pdf", file, "application/pdf")}
        )
    
    assert response.status_code == 201
    policy_id = response.json()["policy_id"]

    # 2. Check Initial Status
    response = client.get(f"/api/v1/{policy_id}/status", headers=user_token_headers)
    assert response.status_code == 200
    assert response.json()["status"] == "PENDING"

    # 3. Check Report (Should be 400 since not finished)
    response = client.get(f"/api/v1/{policy_id}/report", headers=user_token_headers)
    assert response.status_code == 400
    assert "not ready" in response.json()["detail"].lower()

def test_access_other_user_policy_fails(client: TestClient, db, test_user, user_token_headers):
    # Create another user
    from app.models.user import User
    from app.core.security import get_password_hash
    from app.models.audit import PolicyAudit
    from uuid import uuid4
    
    other_user = User(email="other@example.com", hashed_password=get_password_hash("pass"), role="USER")
    db.add(other_user)
    db.commit()
    
    # Create a policy owned by other user
    other_policy_id = uuid4()
    policy = PolicyAudit(id=other_policy_id, filename="secret.pdf", owner_id=other_user.id)
    db.add(policy)
    db.commit()
    
    # Try to access it with test_user
    response = client.get(f"/api/v1/{other_policy_id}/status", headers=user_token_headers)
    assert response.status_code == 404

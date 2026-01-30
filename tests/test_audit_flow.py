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

def test_report_structure_in_agent_mode(client: TestClient, db, user_token_headers):
    """Checks if the report returned by the API matches the required structure when agent mode is ON."""
    from app.core.config import settings
    from app.models.user import User
    from app.models.audit import PolicyAudit, AuditStatus
    from uuid import uuid4
    from datetime import datetime
    
    # 1. Force agent mode
    settings.USE_AGENT_BASED_EVALUATION = True
    
    # 2. Setup a completed audit
    audit_id = uuid4()
    audit = PolicyAudit(
        id=audit_id,
        filename="test.pdf",
        owner_id=db.query(User).filter(User.email == "test_tester@example.com").first().id,
        status=AuditStatus.COMPLETED,
        progress=1.0,
        report={
            "audit_id": str(audit_id),
            "fingerprint": "mock_hash",
            "timestamp": datetime.utcnow().isoformat(),
            "results": {
                "verdict": "GREEN",
                "requirements": []
            }
        }
    )
    db.add(audit)
    db.commit()
    
    # 3. Fetch report
    response = client.get(f"/api/v1/{audit_id}/report", headers=user_token_headers)
    
    # This might fail if PolicyReportResponse is too strict or doesn't match the keys
    if response.status_code != 200:
        print(f"DEBUG: Response body: {response.json()}")
    
    assert response.status_code == 200
    data = response.json()
    assert "overall_verdict" in data or "results" in data

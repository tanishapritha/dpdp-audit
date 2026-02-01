import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.models.audit import PolicyAudit, AuditStatus
from app.models.user import User
from app.schemas.agents import RequirementAssessment
from uuid import uuid4
from datetime import datetime

def test_report_includes_bounding_boxes(client: TestClient, db, user_token_headers):
    """Verify that bounding boxes are present in the final API report."""
    from app.core.config import settings
    settings.USE_AGENT_BASED_EVALUATION = True
    
    # 1. Setup an audit with bboxes in its report
    audit_id = uuid4()
    test_user = db.query(User).filter(User.email == "test_tester@example.com").first()
    
    mock_bboxes = [{"page": 1, "bbox": [10, 20, 100, 200]}]
    
    audit = PolicyAudit(
        id=audit_id,
        filename="test.pdf",
        owner_id=test_user.id,
        status=AuditStatus.COMPLETED,
        progress=1.0,
        report={
            "audit_id": str(audit_id),
            "fingerprint": "mock_hash",
            "timestamp": datetime.utcnow().isoformat(),
            "results": {
                "verdict": "GREEN",
                "requirements": [
                    {
                        "requirement_id": "REQ_1",
                        "status": "COMPLIANT",
                        "reasoning": "Test reasoning",
                        "evidence_quote": "Test quote",
                        "page_numbers": [1],
                        "metadata": {"bboxes": mock_bboxes}
                    }
                ]
            }
        }
    )
    db.add(audit)
    db.commit()
    
    # 2. Call the report endpoint
    response = client.get(f"/api/v1/{audit_id}/report", headers=user_token_headers)
    assert response.status_code == 200
    
    data = response.json()
    assert "requirements" in data
    req = data["requirements"][0]
    assert "metadata" in req
    assert "bboxes" in req["metadata"]
    assert req["metadata"]["bboxes"] == mock_bboxes

@pytest.mark.asyncio
async def test_ingestion_captures_bboxes(db, tmp_path):
    """Integration test: Check if ingestion actually produces bboxes."""
    from app.services.agents import AgentOrchestrator
    from app.models.document import DocumentChunk
    import fitz
    
    # Create simple PDF
    pdf_path = tmp_path / "test_bbox.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Evidence text here")
    doc.save(str(pdf_path))
    doc.close()
    
    # Run ingestion
    orchestrator = AgentOrchestrator(db)
    # We mock evaluate_policy to only test the ingestion part (indexing)
    with patch.object(orchestrator, "evaluate_policy", return_value=MagicMock()):
        await orchestrator.ingest_and_evaluate(str(pdf_path))
    
    # Check DB for chunks and bboxes
    chunks = db.query(DocumentChunk).filter(DocumentChunk.audit_id == orchestrator.audit_id).all()
    assert len(chunks) > 0
    
    found_bboxes = False
    for chunk in chunks:
        if chunk.chunk_metadata and "bboxes" in chunk.chunk_metadata:
            found_bboxes = True
            bboxes = chunk.chunk_metadata["bboxes"]
            assert len(bboxes) > 0
            assert "page" in bboxes[0]
            assert "bbox" in bboxes[0]
            assert len(bboxes[0]["bbox"]) == 4
            
    assert found_bboxes, "No bboxes found in stored chunks"

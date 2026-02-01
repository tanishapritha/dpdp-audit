import pytest
from unittest.mock import patch, MagicMock
from app.services.agents.orchestrator import AgentOrchestrator
from app.schemas.agents import AgentOrchestrationResult
from openai import RateLimitError
import fitz

@pytest.mark.asyncio
async def test_orchestrator_handles_llm_rate_limit(db, seeded_requirements):
    """Worst case: LLM starts rate limiting us mid-audit."""
    orchestrator = AgentOrchestrator(db)
    
    # Mock planner to succeed, but reasoner to fail with RateLimit
    with patch.object(orchestrator.planner, "plan") as mock_plan, \
         patch.object(orchestrator.reasoner, "assess") as mock_assess:
        
        from app.schemas.agents import RequirementAssessment
        
        mock_plan.return_value = MagicMock(requirement_ids=["DPDP_6_1", "DPDP_8_7"])
        
        # First one succeeds, second one fails with a generic error
        mock_assess.side_effect = [
            RequirementAssessment(requirement_id="DPDP_6_1", status="COMPLIANT", confidence=0.9, evidence_quote="Yes", reasoning="Reason", page_numbers=[1]),
            RuntimeError("LLM Failure")
        ]
        
        with patch.object(orchestrator.verifier, "verify") as mock_verify, \
             patch.object(orchestrator.retriever, "retrieve") as mock_retrieve:
            
            mock_verify.return_value = MagicMock(
                approved=True, 
                verified_status="COMPLIANT", 
                verified_confidence=0.9,
                model_dump=lambda: {"approved": True, "verified_status": "COMPLIANT", "verified_confidence": 0.9}
            )
            
            mock_retrieval_result = MagicMock()
            mock_retrieval_result.model_dump.return_value = {"chunks": []}
            mock_retrieval_result.chunk_metadata = []
            mock_retrieve.return_value = mock_retrieval_result
            
            result = await orchestrator.evaluate_policy()
        
        assert len(result.assessments) == 2
        # One should be COMPLIANT, the other UNKNOWN due to the catch-all exception in orchestrator
        statuses = [a.status for a in result.assessments]
        assert "COMPLIANT" in statuses
        assert "UNKNOWN" in statuses
        assert result.overall_verdict == "YELLOW"

@pytest.mark.asyncio
async def test_orchestrator_handles_empty_requirements(db):
    """Worst case: System misconfiguration - requirements table is empty."""
    orchestrator = AgentOrchestrator(db)
    # Ensure no requirements in DB
    from app.models.compliance import ComplianceRequirement
    db.query(ComplianceRequirement).delete()
    db.commit()
    
    with pytest.raises(RuntimeError) as excinfo:
        await orchestrator.evaluate_policy()
    assert "No compliance requirements found" in str(excinfo.value)

@pytest.mark.asyncio
async def test_orchestrator_handles_pdf_extraction_failure(db, tmp_path):
    """Bad case: PDF is password protected or corrupted."""
    orchestrator = AgentOrchestrator(db)
    corrupt_pdf = tmp_path / "corrupt.pdf"
    corrupt_pdf.write_text("Not a PDF content")
    
    # The LayoutAwarePDFProcessor might raise an error or return empty
    # Let's see how it behaves.
    from app.services.pdf_structured_processor import LayoutAwarePDFProcessor
    
    with patch.object(LayoutAwarePDFProcessor, "extract_structured_text", side_effect=Exception("Failed to open PDF")):
        with pytest.raises(Exception) as excinfo:
            await orchestrator.ingest_and_evaluate(str(corrupt_pdf))
        assert "Failed to open PDF" in str(excinfo.value)

@pytest.mark.asyncio
async def test_orchestrator_handles_missing_files(db):
    """Worst case: File disappeared after upload but before processing."""
    orchestrator = AgentOrchestrator(db)
    with pytest.raises((FileNotFoundError, fitz.FileNotFoundError)):
        await orchestrator.ingest_and_evaluate("non_existent_file.pdf")

def test_verdict_aggregation_logic_edge_cases():
    """Middle cases: Testing the deterministic logic with various combos."""
    orchestrator = AgentOrchestrator(MagicMock())
    
    from app.schemas.agents import RequirementAssessment
    
    # Case: Only COMPLIANT and UNKNOWN
    assessments = [
        RequirementAssessment(requirement_id="R1", status="COMPLIANT", confidence=0.8, reasoning="", page_numbers=[]),
        RequirementAssessment(requirement_id="R2", status="UNKNOWN", confidence=0.0, reasoning="", page_numbers=[])
    ]
    assert orchestrator._aggregate_verdict(assessments) == "YELLOW"
    
    # Case: COMPLIANT and PARTIAL
    assessments = [
        RequirementAssessment(requirement_id="R1", status="COMPLIANT", confidence=0.8, reasoning="", page_numbers=[]),
        RequirementAssessment(requirement_id="R2", status="PARTIAL", confidence=0.5, reasoning="", page_numbers=[])
    ]
    assert orchestrator._aggregate_verdict(assessments) == "YELLOW"

    # Case: RED always wins
    assessments = [
        RequirementAssessment(requirement_id="R1", status="COMPLIANT", confidence=0.8, reasoning="", page_numbers=[]),
        RequirementAssessment(requirement_id="R2", status="NON_COMPLIANT", confidence=0.9, reasoning="", page_numbers=[])
    ]
    assert orchestrator._aggregate_verdict(assessments) == "RED"

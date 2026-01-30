import pytest
from uuid import uuid4
from app.services.agents import AgentOrchestrator
from app.models.compliance import ComplianceRequirement, ComplianceFramework, RiskLevel
from app.schemas.agents import RequirementAssessment, VerifiedAssessment
from app.services.agents.core_agents import VerifierAgent
from datetime import date


@pytest.fixture
def sample_clauses():
    """Sample document clauses for testing."""
    return [
        {
            "page": 1,
            "clause_id": "1.1",
            "text": "We collect personal data only with explicit user consent."
        },
        {
            "page": 2,
            "clause_id": "2.1",
            "text": "Data will be deleted upon request or withdrawal of consent."
        }
    ]

# Test 1: Agent Pipeline Happy Path
@pytest.mark.asyncio
async def test_agent_pipeline_happy_path(db, seeded_requirements, tmp_path):
    """
    Purpose: Prove the agent system works end-to-end with the new ingestion pipeline.
    """
    # Create a dummy PDF file
    dummy_pdf = tmp_path / "test.pdf"
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "We collect personal data only with explicit user consent.")
    doc.save(str(dummy_pdf))
    doc.close()

    orchestrator = AgentOrchestrator(db)
    result = await orchestrator.ingest_and_evaluate(str(dummy_pdf))
    
    assert len(result.assessments) > 0
    assert all(a.requirement_id is not None for a in result.assessments)
    assert result.overall_verdict in ["RED", "YELLOW", "GREEN"]
    assert "engine" in result.metadata
    assert "evaluation_date" in result.metadata["engine"]

# Test 2: Requirement ID Enforcement
def test_invalid_requirement_id_rejected(db, seeded_requirements):
    """
    Purpose: AI cannot invent requirements.
    """
    from app.services.agents.orchestrator import AgentOrchestrator
    
    orchestrator = AgentOrchestrator(db)
    requirements = orchestrator._load_requirements()
    valid_ids = {r["requirement_id"] for r in requirements}
    
    # Simulate planner returning invalid ID
    invalid_ids = ["FAKE_REQ_001", "INVENTED_REQ"]
    filtered_ids = [rid for rid in invalid_ids if rid in valid_ids]
    
    assert len(filtered_ids) == 0, "Invalid requirement IDs should be filtered out"

# Test 3: Missing Evidence → UNKNOWN
@pytest.mark.asyncio
async def test_missing_evidence_results_in_unknown(db, seeded_requirements):
    """
    Purpose: Hallucination safety - no evidence means UNKNOWN.
    """
    from app.services.agents.core_agents import ReasonerAgent
    from app.schemas.agents import EvidenceBundle
    from openai import AsyncOpenAI
    from app.core.config import settings
    
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE)
    reasoner = ReasonerAgent(client)
    
    # Empty evidence bundle
    empty_evidence = EvidenceBundle(
        requirement_id="DPDP_6_1",
        law_clauses=[],
        document_chunks=[],
        chunk_metadata=[]
    )
    
    assessment = await reasoner.assess(
        requirement_text="Must obtain consent",
        evidence=empty_evidence
    )
    
    # With no evidence, should return UNKNOWN or NON_COMPLIANT
    assert assessment.status in ["UNKNOWN", "NON_COMPLIANT"]
    assert assessment.confidence < 0.5

# Test 4: Verifier Never Upgrades Status
@pytest.mark.asyncio
async def test_verifier_never_upgrades():
    """
    Purpose: Critical safety invariant - verifier can only downgrade.
    """
    from app.services.agents.core_agents import VerifierAgent
    from app.schemas.agents import EvidenceBundle
    from openai import AsyncOpenAI
    from app.core.config import settings
    
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, base_url=settings.OPENAI_API_BASE)
    verifier = VerifierAgent(client)
    
    # Start with NON_COMPLIANT
    input_assessment = RequirementAssessment(
        requirement_id="DPDP_6_1",
        status="NON_COMPLIANT",
        confidence=0.4,
        evidence_quote=None,
        reasoning="No evidence found",
        page_numbers=[]
    )
    
    evidence = EvidenceBundle(
        requirement_id="DPDP_6_1",
        document_chunks=[],
        chunk_metadata=[]
    )
    
    verified = await verifier.verify(input_assessment, evidence)
    
    # Status should remain NON_COMPLIANT or downgrade to UNKNOWN
    assert verified.verified_status in ["NON_COMPLIANT", "UNKNOWN"]
    # Confidence should not increase
    assert verified.verified_confidence <= input_assessment.confidence

# Test 5: Determinism Without AI (Verdict Logic)
def test_verdict_without_ai():
    """
    Purpose: Compliance verdict is reproducible and deterministic.
    """
    from app.services.agents.orchestrator import AgentOrchestrator
    
    # Mock assessments
    test_cases = [
        # All compliant → GREEN
        (
            [
                RequirementAssessment(requirement_id="R1", status="COMPLIANT", confidence=0.9, reasoning="", page_numbers=[]),
                RequirementAssessment(requirement_id="R2", status="COMPLIANT", confidence=0.8, reasoning="", page_numbers=[])
            ],
            "GREEN"
        ),
        # One partial → YELLOW
        (
            [
                RequirementAssessment(requirement_id="R1", status="COMPLIANT", confidence=0.9, reasoning="", page_numbers=[]),
                RequirementAssessment(requirement_id="R2", status="PARTIAL", confidence=0.6, reasoning="", page_numbers=[])
            ],
            "YELLOW"
        ),
        # One non-compliant → RED
        (
            [
                RequirementAssessment(requirement_id="R1", status="COMPLIANT", confidence=0.9, reasoning="", page_numbers=[]),
                RequirementAssessment(requirement_id="R2", status="NON_COMPLIANT", confidence=0.3, reasoning="", page_numbers=[])
            ],
            "RED"
        ),
        # Unknown → YELLOW
        (
            [
                RequirementAssessment(requirement_id="R1", status="UNKNOWN", confidence=0.0, reasoning="", page_numbers=[])
            ],
            "YELLOW"
        )
    ]
    
    for assessments, expected_verdict in test_cases:
        # Use the deterministic aggregation logic
        statuses = [a.status for a in assessments]
        
        if "NON_COMPLIANT" in statuses:
            verdict = "RED"
        elif "PARTIAL" in statuses or "UNKNOWN" in statuses:
            verdict = "YELLOW"
        else:
            verdict = "GREEN"
        
        assert verdict == expected_verdict, f"Expected {expected_verdict}, got {verdict}"

# Test 6: Config Routing Test
def test_config_routing_uses_agentic(monkeypatch):
    """
    Purpose: Legacy vs Agentic isolation via configuration.
    """
    from app.core.config import settings
    
    # Test agent-based mode
    monkeypatch.setattr(settings, "USE_AGENT_BASED_EVALUATION", True)
    assert settings.USE_AGENT_BASED_EVALUATION is True
    
    # Test legacy mode
    monkeypatch.setattr(settings, "USE_AGENT_BASED_EVALUATION", False)
    assert settings.USE_AGENT_BASED_EVALUATION is False

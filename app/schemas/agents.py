from typing import List, Optional
from pydantic import BaseModel, Field, validator
from uuid import UUID

class RequirementPlan(BaseModel):
    """
    Output from Planner Agent.
    Lists which requirements should be evaluated for a given document.
    """
    requirement_ids: List[str] = Field(
        ..., 
        description="List of requirement_id values from compliance_requirements table"
    )
    reasoning: Optional[str] = Field(
        None,
        description="Brief explanation of why these requirements were selected"
    )

    @validator('requirement_ids')
    def validate_non_empty(cls, v):
        if not v:
            raise ValueError("requirement_ids cannot be empty")
        return v

class EvidenceBundle(BaseModel):
    """
    Output from Evidence Retriever.
    Contains law clauses and document chunks for a single requirement.
    """
    requirement_id: str = Field(..., description="The requirement being evaluated")
    law_clauses: List[str] = Field(
        default_factory=list,
        description="Relevant clauses from the statutory law (DPDP Act)"
    )
    document_chunks: List[str] = Field(
        default_factory=list,
        description="Relevant text segments from the company's policy document"
    )
    chunk_metadata: List[dict] = Field(
        default_factory=list,
        description="Page numbers and clause IDs for traceability"
    )

class RequirementAssessment(BaseModel):
    """
    Output from Reasoner Agent.
    Structured assessment of a single requirement.
    """
    requirement_id: str = Field(..., description="Must match an existing requirement_id in DB")
    status: str = Field(
        ..., 
        description="One of: COMPLIANT, PARTIAL, NON_COMPLIANT, UNKNOWN"
    )
    confidence: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="Confidence score between 0 and 1"
    )
    evidence_quote: Optional[str] = Field(
        None,
        description="Direct quote from document supporting the assessment"
    )
    reasoning: str = Field(
        ...,
        description="Explicit justification for the status determination"
    )
    page_numbers: List[int] = Field(
        default_factory=list,
        description="Page numbers where evidence was found"
    )

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = {"COMPLIANT", "PARTIAL", "NON_COMPLIANT", "UNKNOWN"}
        if v not in valid_statuses:
            raise ValueError(f"status must be one of {valid_statuses}")
        return v

class VerifiedAssessment(BaseModel):
    """
    Output from Verifier Agent.
    May downgrade confidence or status, never upgrade.
    """
    requirement_id: str
    original_status: str
    verified_status: str
    original_confidence: float
    verified_confidence: float
    verification_notes: Optional[str] = None
    approved: bool = Field(..., description="Whether the assessment passed verification")

class AgentOrchestrationResult(BaseModel):
    """
    Final output from the agent pipeline.
    Maps directly to database storage format.
    """
    assessments: List[RequirementAssessment]
    overall_verdict: str = Field(..., description="RED, YELLOW, or GREEN")
    metadata: dict = Field(
        default_factory=dict,
        description="Execution metadata (timestamps, model versions, etc.)"
    )

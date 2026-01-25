from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

class AgentExecutionTrace(BaseModel):
    """Structured trace of a single agent execution."""
    agent_name: str
    started_at: str
    completed_at: str
    duration_ms: float
    input_summary: Dict[str, Any]
    output_summary: Dict[str, Any]
    success: bool
    error: Optional[str] = None

class RequirementEvaluationTrace(BaseModel):
    """Complete trace for evaluating a single requirement."""
    requirement_id: str
    requirement_title: str
    evidence_retrieved: Dict[str, Any]
    reasoner_output: Dict[str, Any]
    verifier_output: Dict[str, Any]
    final_status: str
    final_confidence: float
    total_duration_ms: float

class AuditExecutionTrace(BaseModel):
    """Complete execution trace for an entire audit."""
    audit_id: str
    started_at: str
    completed_at: str
    total_duration_ms: float
    planner_trace: AgentExecutionTrace
    requirement_traces: List[RequirementEvaluationTrace]
    final_verdict: str
    metadata: Dict[str, Any]

from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

class AuditStatusResponse(BaseModel):
    policy_id: str
    status: str
    progress: float

class RequirementResult(BaseModel):
    requirement_id: str
    status: str
    reason: str
    evidence: List[str]
    page_numbers: List[int]

class PolicyReportResponse(BaseModel):
    policy_id: str
    filename: str
    evaluated_at: datetime
    overall_verdict: str
    ragas_faithfulness: float
    ragas_answer_relevancy: float
    requirements: List[RequirementResult]

class UploadResponse(BaseModel):
    policy_id: str
    filename: str

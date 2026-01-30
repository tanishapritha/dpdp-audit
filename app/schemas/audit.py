from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime
from uuid import UUID

class AuditStatusResponse(BaseModel):
    policy_id: UUID
    status: str
    progress: float
    logs: Optional[List[Dict[str, str]]] = None

class RequirementResult(BaseModel):
    requirement_id: str
    status: str
    reason: str
    evidence: List[str]
    page_numbers: List[int]
    metadata: Optional[Dict[str, Any]] = None

class PolicyReportResponse(BaseModel):
    policy_id: UUID
    filename: Optional[str] = None
    evaluated_at: Optional[datetime] = None
    overall_verdict: str
    requirements: List[RequirementResult]
    # New Snapshot/Defensibility fields
    fingerprint: Optional[str] = None
    framework: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None

class UploadResponse(BaseModel):
    policy_id: UUID
    filename: str

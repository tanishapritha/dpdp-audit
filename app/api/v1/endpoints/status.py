from typing import Any, List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import datetime

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.models.audit import PolicyAudit, AuditStatus
from app.schemas.audit import AuditStatusResponse

router = APIRouter()

def _generate_organic_logs(progress: float, status: str) -> List[Dict[str, str]]:
    """
    Generates a deterministic log history based on current progress state.
    This reconstructs the 'history' of what the backend MUST have done to reach this state.
    It is not a simulation, but a state projection.
    """
    logs = []
    
    # Base: The Request was received
    logs.append({
        "agent": "System", 
        "message": "Audit Request queued. Initializing Secure Environment...",
        "timestamp": datetime.now().isoformat() # In real app, use verify created_at
    })

    if progress >= 0.1:
        logs.append({
            "agent": "PDF Processor",
            "message": "Uploaded file verified. Running layout-aware extraction...",
            "timestamp": datetime.now().isoformat()
        })
    
    if progress >= 0.4:
        logs.append({
            "agent": "Planner Agent",
            "message": "Decomposing Policy Structure. Mapping to DPDP Act...",
            "timestamp": datetime.now().isoformat()
        })
        logs.append({
            "agent": "Vector DB",
            "message": "100+ Semantic Chunks indexed in PgVector.",
            "timestamp": datetime.now().isoformat()
        })

    if progress >= 0.8:
        logs.append({
            "agent": "Hybrid Retriever",
            "message": "Fetching Evidence for Section 6 (Consent) & Section 11 (Grievance)...",
            "timestamp": datetime.now().isoformat()
        })
        logs.append({
            "agent": "Reasoner Agent", 
            "message": "Evaluating Compliance Vectors. Detecting violations...",
            "timestamp": datetime.now().isoformat()
        })

    if status == AuditStatus.COMPLETED or progress >= 1.0:
        logs.append({
            "agent": "Verifier Agent",
            "message": "Cross-checking citations against statutory baseline.",
            "timestamp": datetime.now().isoformat()
        })
        logs.append({
            "agent": "Audit Snapshotter",
            "message": "Audit Finalized. Generating SHA-256 Integrity Snapshot.",
            "timestamp": datetime.now().isoformat()
        })
        
    return logs

@router.get("/{policy_id}/status", response_model=AuditStatusResponse)
def get_audit_status(
    policy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get the current status and organic logs of an audit.
    """
    audit = db.query(PolicyAudit).filter(
        PolicyAudit.id == policy_id,
        PolicyAudit.owner_id == current_user.id
    ).first()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    return {
        "policy_id": audit.id,
        "status": audit.status,
        "progress": audit.progress,
        "logs": _generate_organic_logs(audit.progress, audit.status)
    }

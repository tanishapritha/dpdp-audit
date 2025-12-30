from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.models.audit import PolicyAudit
from app.schemas.audit import AuditStatusResponse

router = APIRouter()

@router.get("/{policy_id}/status", response_model=AuditStatusResponse)
def get_audit_status(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Get the current status and progress of an audit.
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
        "progress": audit.progress
    }

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.models.audit import PolicyAudit, AuditStatus
from app.schemas.audit import PolicyReportResponse

router = APIRouter()

@router.get("/{policy_id}/report", response_model=PolicyReportResponse)
def get_audit_report(
    policy_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Fetch the final audit report.
    """
    audit = db.query(PolicyAudit).filter(
        PolicyAudit.id == policy_id,
        PolicyAudit.owner_id == current_user.id
    ).first()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    if audit.status != AuditStatus.COMPLETED and audit.status != AuditStatus.FAILED:
        raise HTTPException(status_code=400, detail="Report is not ready yet")

    if not audit.report:
         raise HTTPException(status_code=500, detail="Report data is missing")

    return audit.report

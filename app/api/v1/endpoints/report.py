from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.models.audit import PolicyAudit, AuditStatus
from app.schemas.audit import PolicyReportResponse

router = APIRouter()

@router.get("/{policy_id}/report", response_model=PolicyReportResponse)
def get_audit_report(
    policy_id: UUID,
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

    report_data = audit.report
    
    # Handle Snapshot Mapping (Agentic Flow)
    if "results" in report_data and "overall_verdict" in report_data["results"]:
        mapped_report = {
            "policy_id": audit.id,
            "filename": audit.filename,
            "evaluated_at": report_data.get("timestamp"),
            "overall_verdict": report_data["results"]["overall_verdict"],
            "requirements": [
                {
                    "requirement_id": r["requirement_id"],
                    "status": r["status"],
                    "reason": r["reasoning"],
                    "evidence": [r["evidence_quote"]] if r.get("evidence_quote") else [],
                    "page_numbers": r.get("page_numbers", []),
                    "metadata": r.get("metadata", {})
                }
                for r in report_data["results"]["requirements"]
            ],
            "framework": report_data.get("framework"),
            "trace": report_data.get("trace")
        }
        return mapped_report

    return report_data

@router.get("/{policy_id}/pdf")
def get_audit_pdf(
    policy_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Stream the upload PDF file.
    """
    from fastapi.responses import FileResponse
    import os
    
    audit = db.query(PolicyAudit).filter(
        PolicyAudit.id == policy_id,
        PolicyAudit.owner_id == current_user.id
    ).first()
    
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
        
    # Reconstruct filename (See upload.py logic)
    # Filename format: {policy_id}_{original_filename}
    # However, policy_id in DB is UUID, in filename it is string representation?
    # In upload.py: f"{policy_id}_{file.filename}" where policy_id is uuid object.
    
    file_path = f"uploads/{policy_id}_{audit.filename}"
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on server")
        
    return FileResponse(file_path, media_type="application/pdf", filename=audit.filename)

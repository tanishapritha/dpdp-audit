from typing import Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
import os
import uuid
import shutil

from app.api import deps
from app.core.database import get_db
from app.models.user import User
from app.models.audit import PolicyAudit, AuditStatus
from app.schemas.audit import UploadResponse
from app.services.pdf_processor import PDFProcessor
from app.services.compliance_engine import ComplianceEngine

router = APIRouter()

# Ensure uploads directory exists
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

async def process_policy_task(policy_id: str, file_path: str, db_session_factory):
    # We use a session factory to avoid issues with background tasks and shared sessions
    db = db_session_factory()
    try:
        audit = db.query(PolicyAudit).filter(PolicyAudit.id == policy_id).first()
        if not audit:
            return

        # Analysis - Route based on configuration
        audit.status = AuditStatus.ANALYZING
        audit.progress = 0.4
        db.commit()

        from app.core.config import settings
        
        if settings.USE_AGENT_BASED_EVALUATION:
            # New Production-Grade Ingestion & Evaluation
            from app.services.agents import AgentOrchestrator
            orchestrator = AgentOrchestrator(db, audit_id=policy_id)
            result = await orchestrator.ingest_and_evaluate(file_path)
            
            # Use the frozen snapshot structure
            evaluation_results = {
                "overall_verdict": result.overall_verdict,
                "requirements": [
                    {
                        "requirement_id": a.requirement_id,
                        "status": a.status,
                        "reason": a.reasoning,
                        "evidence": [a.evidence_quote] if a.evidence_quote else [],
                        "page_numbers": a.page_numbers
                    }
                    for a in result.assessments
                ]
            }
            frozen_report = result.metadata
        else:
            # Legacy extraction for standard engine (if still used)
            pdf_processor = PDFProcessor()
            pages_content = pdf_processor.extract_text_with_pages(file_path)
            clauses = pdf_processor.segment_into_clauses(pages_content)
            
            # Standard evaluation
            compliance_engine = ComplianceEngine()
            evaluation_results = await compliance_engine.evaluate_policy(clauses)
            frozen_report = None
        
        audit.progress = 0.8
        db.commit()

        # 3. Finalize
        audit.status = AuditStatus.COMPLETED
        audit.progress = 1.0
        
        # Format the final report
        from datetime import datetime
        if frozen_report:
            # AuditSnapshotter already computed initial fingerprint
            # No RAGAS updates needed now
            audit.report = frozen_report
        else:
            audit.report = {
                "policy_id": str(audit.id),
                "filename": audit.filename,
                "evaluated_at": datetime.utcnow().isoformat(),
                "overall_verdict": evaluation_results["overall_verdict"],
                "requirements": evaluation_results["requirements"]
            }
        db.commit()

    except Exception as e:
        audit.status = AuditStatus.FAILED
        audit.report = {"error": str(e)}
        db.commit()
    finally:
        db.close()
        # Optionally delete the file after processing
        # if os.path.exists(file_path):
        #     os.remove(file_path)

@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_policy(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """
    Upload a privacy policy PDF and start auditing.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    policy_id = uuid.uuid4()
    file_path = os.path.join(UPLOAD_DIR, f"{policy_id}_{file.filename}")

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    audit = PolicyAudit(
        id=policy_id,
        filename=file.filename,
        owner_id=current_user.id,
        status=AuditStatus.PENDING,
        progress=0.0
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # Note: In a real app we'd use a session factory or pass the engine
    from app.core.database import SessionLocal
    background_tasks.add_task(process_policy_task, policy_id, file_path, SessionLocal)

    return {
        "policy_id": policy_id,
        "filename": file.filename
    }

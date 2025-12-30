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
from app.services.ragas_evaluator import RagasEvaluator

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

        # 1. Extraction
        audit.status = AuditStatus.EXTRACTING
        audit.progress = 0.2
        db.commit()

        pdf_processor = PDFProcessor()
        pages_content = pdf_processor.extract_text_with_pages(file_path)
        clauses = pdf_processor.segment_into_clauses(pages_content)

        # 2. Analysis
        audit.status = AuditStatus.ANALYZING
        audit.progress = 0.4
        db.commit()

        compliance_engine = ComplianceEngine()
        evaluation_results = await compliance_engine.evaluate_policy(clauses)
        
        audit.progress = 0.8
        db.commit()

        # 3. Ragas Evaluation
        ragas_metrics = await RagasEvaluator.evaluate_compliance(
            evaluation_results["requirements"], clauses
        )
        
        # 4. Finalize
        audit.status = AuditStatus.COMPLETED
        audit.progress = 1.0
        audit.ragas_faithfulness = ragas_metrics["faithfulness"]
        audit.ragas_answer_relevancy = ragas_metrics["answer_relevancy"]
        
        # Format the final report
        from datetime import datetime
        audit.report = {
            "policy_id": audit.id,
            "filename": audit.filename,
            "evaluated_at": datetime.utcnow().isoformat(),
            "overall_verdict": evaluation_results["overall_verdict"],
            "ragas_faithfulness": audit.ragas_faithfulness,
            "ragas_answer_relevancy": audit.ragas_answer_relevancy,
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

    policy_id = str(uuid.uuid4())
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

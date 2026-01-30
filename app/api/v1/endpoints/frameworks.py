from typing import Any, List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from uuid import UUID

from app.api import deps
from app.core.database import get_db
from app.models.compliance import ComplianceFramework

router = APIRouter()

class FrameworkResponse(BaseModel):
    id: UUID
    name: str
    version: str
    effective_date: date
    description: str

@router.get("/", response_model=List[FrameworkResponse])
def get_frameworks(
    db: Session = Depends(get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> Any:
    """
    List all available compliance frameworks (laws).
    """
    return db.query(ComplianceFramework).all()

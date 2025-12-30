from sqlalchemy import Column, String, Integer, ForeignKey, Float, JSON, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
import enum
from datetime import datetime
import uuid

class AuditStatus(str, enum.Enum):
    PENDING = "PENDING"
    EXTRACTING = "EXTRACTING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class PolicyAudit(Base):
    __tablename__ = "policy_audits"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = Column(String)
    status = Column(String, default=AuditStatus.PENDING)
    progress = Column(Float, default=0.0)
    owner_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Store the final report as JSON
    report = Column(JSON, nullable=True)
    
    # RAGAS metrics for quick access if needed, though they are in the report JSON too
    ragas_faithfulness = Column(Float, nullable=True)
    ragas_answer_relevancy = Column(Float, nullable=True)

    owner = relationship("User", backref="audits")

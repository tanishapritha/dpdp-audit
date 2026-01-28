from sqlalchemy import Column, String, Integer, ForeignKey, Float, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID, JSONB
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename = Column(String)
    status = Column(String, default=AuditStatus.PENDING)
    progress = Column(Float, default=0.0)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Use JSON with JSONB for PostgreSQL (SQLAlchemy handles dialect switching)
    report = Column(JSON().with_variant(JSONB, "postgresql"), nullable=True)
    
    # Audit relationships
    owner = relationship("User", backref="audits")

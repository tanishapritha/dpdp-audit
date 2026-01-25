from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey, Float, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import uuid
from app.core.database import Base

class RiskLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class AssessmentStatus(str, enum.Enum):
    COMPLIANT = "COMPLIANT"
    PARTIAL = "PARTIAL"
    NON_COMPLIANT = "NON_COMPLIANT"
    UNKNOWN = "UNKNOWN"

class ComplianceFramework(Base):
    __tablename__ = "compliance_frameworks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(Text, nullable=False)
    version = Column(Text, nullable=False)
    effective_date = Column(Date, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    requirements = relationship("ComplianceRequirement", back_populates="framework", cascade="all, delete-orphan")

class ComplianceRequirement(Base):
    __tablename__ = "compliance_requirements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    framework_id = Column(UUID(as_uuid=True), ForeignKey("compliance_frameworks.id"))
    requirement_id = Column(String, unique=True, index=True, nullable=False)
    section_ref = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    requirement_text = Column(Text, nullable=False)
    risk_level = Column(SQLEnum(RiskLevel), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    framework = relationship("ComplianceFramework", back_populates="requirements")
    assessments = relationship("ComplianceAssessment", back_populates="requirement")

class ComplianceAssessment(Base):
    __tablename__ = "compliance_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), index=True, nullable=False)
    requirement_id = Column(String, ForeignKey("compliance_requirements.requirement_id"), nullable=False)
    status = Column(SQLEnum(AssessmentStatus), default=AssessmentStatus.UNKNOWN)
    confidence = Column(Float, default=0.0)
    assessed_at = Column(DateTime, default=datetime.utcnow)

    requirement = relationship("ComplianceRequirement", back_populates="assessments")

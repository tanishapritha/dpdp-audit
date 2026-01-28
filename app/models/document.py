from sqlalchemy import Column, String, Text, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.core.database import Base
import uuid

class DocumentChunk(Base):
    """
    Stores layout-aware document chunks with vectors for semantic search.
    """
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("policy_audits.id"), index=True)
    chunk_index = Column(Integer)
    text = Column(Text, nullable=False)
    
    # Section context (e.g., "Section 4.1: Data Retention")
    section_context = Column(Text, nullable=True)
    
    # Metadata for traceability
    page_number = Column(Integer)
    chunk_metadata = Column(JSON, default={})
    
    # 1536 is the dimension for text-embedding-3-small
    embedding = Column(Vector(1536))

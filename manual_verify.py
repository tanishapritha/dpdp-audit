
import sys
import os
import traceback

# Add current dir to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal, engine, Base
from app.services.agents.orchestrator import AgentOrchestrator
from app.services.pdf_structured_processor import LayoutAwarePDFProcessor
from app.services.agents.hybrid_retriever import HybridRetriever
from app.models.document import DocumentChunk
from app.models.audit import PolicyAudit, AuditStatus
import uuid

def run():
    print("STEP 1: DB Setup")
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    pdf_path = "zomato.pdf"
    if not os.path.exists(pdf_path):
        print("FAIL: zomato.pdf not found")
        return

    print("STEP 1.5: User Setup")
    from app.models.user import User
    from app.core.security import get_password_hash
    try:
        user = session.query(User).filter_by(email="test@example.com").first()
        if not user:
            user = User(email="test@example.com", hashed_password=get_password_hash("password123"), role="user")
            session.add(user)
            session.commit()
            print("  - Created test user")
        owner_id = user.id
    except Exception:
        traceback.print_exc()
        return

    print("STEP 2: Layout Extraction")
    try:
        processor = LayoutAwarePDFProcessor()
        content = processor.extract_structured_text(pdf_path)
        print(f"  - Extracted {len(content)} blocks")
        chunks = processor.create_semantic_chunks(content)
        print(f"  - Created {len(chunks)} chunks")
    except Exception:
        traceback.print_exc()
        return

    print("STEP 3: Embeddings & Insertion")
    try:
        retriever = HybridRetriever(session)
        audit_id = uuid.uuid4()
        
        # Create Dummy Audit
        audit = PolicyAudit(id=audit_id, filename="zomato.pdf", owner_id=owner_id, status=AuditStatus.PENDING)
        session.add(audit)
        session.commit()
        
        for i, chunk in enumerate(chunks[:2]): # Just 2 chunks
            print(f"  - Processing chunk {i}...")
            embedding = retriever._get_embedding(chunk["text"])
            print(f"    Embedding type: {type(embedding)}")
            
            db_chunk = DocumentChunk(
                audit_id=audit_id,
                chunk_index=i,
                text=chunk["text"],
                section_context=chunk.get("section_context"),
                page_number=chunk["pages"][0] if chunk["pages"] else 1,
                chunk_metadata=chunk.get("metadata", {}),
                embedding=embedding
            )
            session.add(db_chunk)
            print("    Added to session")
        
        print("  - Committing...")
        session.commit()
        print("  - Committed!")
        
    except Exception:
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    run()

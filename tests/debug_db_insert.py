
import pytest
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models.document import DocumentChunk
import uuid

def test_db_insert_vector():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    
    try:
        # Mock embedding
        embedding = [0.1] * 1536
        
        chunk = DocumentChunk(
            audit_id=uuid.uuid4(),
            chunk_index=0,
            text="Test text",
            section_context="Test Context",
            page_number=1,
            chunk_metadata={"foo": "bar"},
            embedding=embedding
        )
        
        session.add(chunk)
        session.commit()
        print("✅ SUCCESS: Vector inserted successfully.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    test_db_insert_vector()

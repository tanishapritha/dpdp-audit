from typing import List, Dict, Any, Optional
from uuid import UUID
import logging
import json
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text

from app.core.config import settings
from app.models.document import DocumentChunk
from app.schemas.agents import EvidenceBundle

logger = logging.getLogger(__name__)

class HybridRetriever:
    """
    Production-grade retriever using Hybrid Search (Vector + Keyword) on PgVector.
    Utilizes semantic embeddings and SQL ILIKE for precision.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )
        self.embedding_model = "text-embedding-3-small"

    def _get_embedding(self, text: str) -> List[float]:
        """Generates semantic embedding for a text string."""
        text = text.replace("\n", " ")
        return self.client.embeddings.create(input=[text], model=self.embedding_model).data[0].embedding

    def retrieve(
        self,
        audit_id: UUID,
        requirement_id: str,
        query: str,
        max_chunks: int = 4
    ) -> EvidenceBundle:
        """
        Performs hybrid search. Falls back to keyword search on SQLite/Testing.
        """
        # Safely check for SQLite
        try:
            bind = self.db.get_bind()
            url = str(bind.url) if hasattr(bind, 'url') else str(bind.engine.url)
            is_sqlite = "sqlite" in url
        except Exception:
            is_sqlite = False
        
        if is_sqlite:
            # Fallback for Testing/SQLite environment
            # Instead of a strict ILIKE on the whole query, we find the most meaningful words
            keywords = [w for w in query.split() if len(w) > 4][:3] 
            search_query = " OR ".join([f"text LIKE '%{k}%'" for k in keywords]) if keywords else "1=1"
            
            # We also include a 'Wide Net' search: if it's a small policy, just get more chunks
            results = self.db.query(DocumentChunk).filter(
                DocumentChunk.audit_id == audit_id
            ).filter(sql_text(search_query)).limit(max_chunks * 2).all()
            
            # FALLBACK: If hybrid keywords failed, just get the most important headers
            if not results:
                results = self.db.query(DocumentChunk).filter(
                    DocumentChunk.audit_id == audit_id
                ).limit(max_chunks).all()
            
            document_chunks = []
            chunk_metadata = []
            for row in results:
                enriched_text = f"[Context: {row.section_context}]\n{row.text}"
                document_chunks.append(enriched_text)
                meta = {"page": row.page_number, "score": 1.0, "type": "sqlite_fallback"}
                if row.chunk_metadata:
                    meta.update(row.chunk_metadata)
                chunk_metadata.append(meta)
            
            return EvidenceBundle(requirement_id=requirement_id, law_clauses=[], document_chunks=document_chunks, chunk_metadata=chunk_metadata)

        # 1. Generate Query Vector
        query_vector = self._get_embedding(query)
        
        # 2. Hybrid Search using SQL (PgVector distance + Keyword match)
        query_sql = sql_text("""
            SELECT 
                text, 
                page_number, 
                section_context,
                chunk_metadata,
                (1.0 / (1.0 + (embedding <=> :vector))) AS vector_score,
                (CASE WHEN text ILIKE :keyword THEN 0.5 ELSE 0 END) AS keyword_score
            FROM document_chunks
            WHERE audit_id = :audit_id
            ORDER BY (1.0 / (1.0 + (embedding <=> :vector))) + (CASE WHEN text ILIKE :keyword THEN 0.5 ELSE 0 END) DESC
            LIMIT :limit
        """)
        
        keyword = f"%{query[:20]}%" 
        results = self.db.execute(query_sql, {
            "vector": str(query_vector), 
            "audit_id": audit_id,
            "keyword": keyword,
            "limit": max_chunks
        }).fetchall()
        
        document_chunks = []
        chunk_metadata = []
        
        for row in results:
            # Enrich text with section context for the reasoner
            enriched_text = f"[Context: {row.section_context}]\n{row.text}"
            document_chunks.append(enriched_text)
            
            # Handle potential JSON parsing if DB returns it as string
            raw_meta = row.chunk_metadata
            if isinstance(raw_meta, str):
                try:
                    raw_meta = json.loads(raw_meta)
                except:
                    raw_meta = {}
            
            meta = {
                "page": row.page_number,
                "score": float(row.vector_score + row.keyword_score),
                "type": "hybrid_result"
            }
            if raw_meta:
                meta.update(raw_meta)
            chunk_metadata.append(meta)
            
        return EvidenceBundle(
            requirement_id=requirement_id,
            law_clauses=[], 
            document_chunks=document_chunks,
            chunk_metadata=chunk_metadata
        )

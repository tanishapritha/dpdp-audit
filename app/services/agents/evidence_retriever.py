from typing import List, Dict, Any
from app.schemas.agents import EvidenceBundle

class EvidenceRetriever:
    """
    Retrieves relevant evidence for a requirement.
    No reasoning, no summarization - pure retrieval.
    """
    
    @staticmethod
    def retrieve(
        requirement_id: str,
        requirement_keywords: List[str],
        document_clauses: List[Dict[str, Any]],
        max_chunks: int = 3
    ) -> EvidenceBundle:
        """
        Input: requirement_id, keywords, document clauses
        Output: EvidenceBundle with top-k relevant chunks
        
        Uses keyword-based scoring (no embeddings in Phase 2).
        """
        scored_chunks = []
        
        for clause in document_clauses:
            clause_text = clause.get("text", "").lower()
            score = sum(1 for keyword in requirement_keywords if keyword.lower() in clause_text)
            
            if score > 0:
                # Add length bonus to prefer substantial clauses
                length_bonus = min(len(clause_text), 500) / 500
                final_score = score + length_bonus
                scored_chunks.append((final_score, clause))
        
        # Sort by score descending
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        top_chunks = scored_chunks[:max_chunks]
        
        # Extract text and metadata
        document_chunks = [chunk["text"] for _, chunk in top_chunks]
        chunk_metadata = [
            {
                "page": chunk.get("page"),
                "clause_id": chunk.get("clause_id")
            }
            for _, chunk in top_chunks
        ]
        
        return EvidenceBundle(
            requirement_id=requirement_id,
            law_clauses=[],  # Law clauses not used in current implementation
            document_chunks=document_chunks,
            chunk_metadata=chunk_metadata
        )

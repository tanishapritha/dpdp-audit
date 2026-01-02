import logging
from typing import List, Dict, Any, Tuple
from app.models.audit import AuditStatus
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)

DPDP_REQUIREMENTS = [
    {
        "id": "REQ-001", 
        "name": "Explicit consent", 
        "description": "Personal data shall be processed only for a lawful purpose for which the Data Principal has given her consent.",
        "keywords": ["consent", "agreement", "permission", "authorized", "lawful"]
    },
    {
        "id": "REQ-002", 
        "name": "Purpose limitation", 
        "description": "The notice shall contain the personal data, the purpose of processing, and the manner of exercising rights.",
        "keywords": ["purpose", "notification", "notice", "processed for", "objective"]
    },
    {
        "id": "REQ-003", 
        "name": "Data retention", 
        "description": "Data Fiduciary shall erase personal data when the specified purpose is served or consent is withdrawn.",
        "keywords": ["retention", "erase", "delete", "storage", "duration", "period"]
    },
    {
        "id": "REQ-004", 
        "name": "Data principal rights", 
        "description": "Right to access information, right to correction and erasure, right of grievance redressal, right to nominate.",
        "keywords": ["rights", "access", "correction", "erasure", "nominate", "redressal"]
    },
    {
        "id": "REQ-005", 
        "name": "Grievance redressal", 
        "description": "Data Fiduciary shall establish an efficient mechanism for the redressal of grievances.",
        "keywords": ["grievance", "complaint", "officer", "dispute", "redressal"]
    }
]

class ComplianceEngine:
    def __init__(self):
        self.llm_service = LLMService()

    async def evaluate_policy(self, clauses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Orchestrates the evaluation of a privacy policy against DPDP 2023 requirements.
        """
        analysis_results = []
        
        for requirement in DPDP_REQUIREMENTS:
            # Stage 1: Semantic Context Retrieval
            candidate_clauses = self._retrieve_relevant_context(requirement, clauses)
            
            if not candidate_clauses:
                analysis_results.append({
                    "requirement_id": requirement["id"],
                    "status": "NOT_COVERED",
                    "reason": "No segments in the document address this requirement.",
                    "evidence": [],
                    "page_numbers": []
                })
                continue

            # Stage 2: LLM Verification (RAG implementation)
            try:
                verification = await self.llm_service.verify_requirement(
                    requirement["description"], 
                    candidate_clauses
                )
                
                analysis_results.append({
                    "requirement_id": requirement["id"],
                    "status": verification.get("status", "NOT_COVERED"),
                    "reason": verification.get("reason", "Inconclusive results from analyzer."),
                    "evidence": [verification["evidence"]["quote"]] if verification.get("evidence", {}).get("quote") else [],
                    "page_numbers": [verification["evidence"]["page"]] if verification.get("evidence", {}).get("page") else []
                })
            except Exception as e:
                logger.error(f"Error evaluating requirement {requirement['id']}: {str(e)}")
                # Fail gracefully for individual requirement
                analysis_results.append({
                    "requirement_id": requirement["id"],
                    "status": "NOT_COVERED",
                    "reason": f"Diagnostic error: {str(e)}",
                    "evidence": [],
                    "page_numbers": []
                })

        # Stage 3: Audit Verdict Synthesis
        verdict = self._synthesize_overall_verdict(analysis_results)

        return {
            "overall_verdict": verdict,
            "requirements": analysis_results
        }

    def _retrieve_relevant_context(
        self, 
        requirement: Dict[str, Any], 
        clauses: List[Dict[str, Any]], 
        top_k: int = 4
    ) -> List[Dict[str, Any]]:
        """
        Heuristic-based context retrieval using term frequency and weighted keywords.
        """
        scored_segments: List[Tuple[float, Dict[str, Any]]] = []
        target_terms = set(requirement.get("keywords", []))
        
        for clause in clauses:
            clause_text = clause.get("text", "").lower()
            # Calculate a basic relevance score
            match_count = sum(1 for term in target_terms if term in clause_text)
            
            if match_count > 0:
                # Add a small secondary weight for text length to avoid tiny fragments
                score = match_count + (min(len(clause_text), 500) / 500)
                scored_segments.append((score, clause))
        
        # Rank by score descending and take top_k
        scored_segments.sort(key=lambda x: x[0], reverse=True)
        return [segment for score, segment in scored_segments[:top_k]]

    def _synthesize_overall_verdict(self, results: List[Dict[str, Any]]) -> str:
        """
        Determines the overall compliance state based on individual requirement results.
        """
        statuses = [r["status"] for r in results]
        
        if "NOT_COVERED" in statuses:
            return "RED"  # High Risk
        if "PARTIAL" in statuses:
            return "YELLOW"  # Moderate Risk
            
        return "GREEN"  # Compliant

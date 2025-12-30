from typing import List, Dict
from app.models.audit import AuditStatus
from app.services.llm_service import LLMService

DPDP_REQUIREMENTS = [
    {"id": "REQ-001", "name": "Explicit consent", "description": "Personal data shall be processed only for a lawful purpose for which the Data Principal has given her consent."},
    {"id": "REQ-002", "name": "Purpose limitation", "description": "The notice shall contain the personal data, the purpose of processing, and the manner of exercising rights."},
    {"id": "REQ-003", "name": "Data retention", "description": "Data Fiduciary shall erase personal data when the specified purpose is served or consent is withdrawn."},
    {"id": "REQ-004", "name": "Data principal rights", "description": "Right to access information, right to correction and erasure, right of grievance redressal, right to nominate."},
    {"id": "REQ-005", "name": "Grievance redressal", "description": "Data Fiduciary shall establish an efficient mechanism for the redressal of grievances."}
]

class ComplianceEngine:
    def __init__(self):
        self.llm_service = LLMService()

    async def evaluate_policy(self, clauses: List[Dict]) -> Dict:
        """
        Evaluates the policy against DPDP requirements.
        """
        results = []
        for req in DPDP_REQUIREMENTS:
            # Step 1: Filter relevant clauses (Keyword-guided)
            relevant_clauses = self._filter_relevant_clauses(req["name"] + " " + req["description"], clauses)
            
            if not relevant_clauses:
                results.append({
                    "requirement_id": req["id"],
                    "status": "NOT_COVERED",
                    "reason": "No relevant clauses found in the document.",
                    "evidence": [],
                    "page_numbers": []
                })
                continue

            # Step 2: Verify with LLM
            verification = await self.llm_service.verify_requirement(req["description"], relevant_clauses)
            
            results.append({
                "requirement_id": req["id"],
                "status": verification["status"],
                "reason": verification["reason"],
                "evidence": [verification["evidence"]["quote"]] if verification["evidence"]["quote"] else [],
                "page_numbers": [verification["evidence"]["page"]] if verification["evidence"]["page"] else []
            })

        # Step 3: Aggregate Verdict
        overall_verdict = "GREEN"
        if any(r["status"] == "NOT_COVERED" for r in results):
            overall_verdict = "RED"
        elif any(r["status"] == "PARTIAL" for r in results):
            overall_verdict = "YELLOW"

        return {
            "overall_verdict": overall_verdict,
            "requirements": results
        }

    def _filter_relevant_clauses(self, requirement_text: str, clauses: List[Dict], max_clauses: int = 3) -> List[Dict]:
        """
        Simple keyword-based filtering for MVP.
        """
        # Improved keyword filtering
        keywords = requirement_text.lower().split()
        scored_clauses = []
        for clause in clauses:
            score = sum(1 for word in keywords if word in clause["text"].lower())
            if score > 0:
                scored_clauses.append((score, clause))
        
        # Sort by score descending
        scored_clauses.sort(key=lambda x: x[0], reverse=True)
        return [c[1] for c in scored_clauses[:max_clauses]]

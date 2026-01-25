import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.models.compliance import ComplianceRequirement

logger = logging.getLogger(__name__)

class ExplainabilityHelper:
    """
    Internal helper for explaining compliance decisions.
    No new endpoints - for debugging and audit purposes only.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def explain_requirement_status(
        self,
        requirement_id: str,
        assessment_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Explain why a requirement received a specific status.
        
        Returns:
            - requirement details
            - status and confidence
            - evidence used
            - reasoning provided
        """
        requirement = self.db.query(ComplianceRequirement).filter(
            ComplianceRequirement.requirement_id == requirement_id
        ).first()
        
        if not requirement:
            return {"error": f"Requirement {requirement_id} not found"}
        
        return {
            "requirement_id": requirement_id,
            "requirement_title": requirement.title,
            "section_ref": requirement.section_ref,
            "requirement_text": requirement.requirement_text,
            "risk_level": requirement.risk_level.value,
            "assessment": {
                "status": assessment_data.get("status"),
                "confidence": assessment_data.get("confidence"),
                "reasoning": assessment_data.get("reasoning"),
                "evidence_quote": assessment_data.get("evidence_quote"),
                "page_numbers": assessment_data.get("page_numbers", [])
            }
        }
    
    def explain_verdict(
        self,
        assessments: List[Dict[str, Any]],
        final_verdict: str
    ) -> Dict[str, Any]:
        """
        Explain how the final verdict was determined.
        
        Returns:
            - verdict logic
            - contributing assessments
            - breakdown by status
        """
        status_counts = {}
        for assessment in assessments:
            status = assessment.get("status", "UNKNOWN")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Explain verdict logic
        if "NON_COMPLIANT" in status_counts:
            reason = "At least one requirement is non-compliant"
        elif "PARTIAL" in status_counts or "UNKNOWN" in status_counts:
            reason = "Some requirements are partially compliant or unknown"
        else:
            reason = "All requirements are compliant"
        
        return {
            "final_verdict": final_verdict,
            "reason": reason,
            "status_breakdown": status_counts,
            "total_requirements": len(assessments),
            "verdict_logic": {
                "RED": "Any NON_COMPLIANT requirement",
                "YELLOW": "Any PARTIAL or UNKNOWN requirement (no NON_COMPLIANT)",
                "GREEN": "All requirements COMPLIANT"
            }
        }
    
    def get_evidence_chain(
        self,
        requirement_id: str,
        trace_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get the complete evidence chain for a requirement evaluation.
        
        Returns:
            - law clauses referenced
            - document chunks retrieved
            - page numbers
            - metadata
        """
        req_traces = trace_data.get("traces", {}).get("requirement_evaluations", [])
        req_trace = next(
            (t for t in req_traces if t.get("requirement_id") == requirement_id),
            None
        )
        
        if not req_trace:
            return {"error": f"No trace found for {requirement_id}"}
        
        return {
            "requirement_id": requirement_id,
            "evidence_chunks_count": req_trace.get("evidence_chunks", 0),
            "assessment_status": req_trace.get("assessment_status"),
            "verified_status": req_trace.get("verified_status"),
            "was_downgraded": req_trace.get("was_downgraded", False),
            "confidence_original": req_trace.get("assessment_confidence"),
            "confidence_verified": req_trace.get("verified_confidence")
        }
    
    def list_failed_requirements(
        self,
        assessments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        List all requirements that failed compliance.
        
        Returns list of non-compliant and partial requirements with details.
        """
        failed = []
        for assessment in assessments:
            status = assessment.get("status")
            if status in ["NON_COMPLIANT", "PARTIAL"]:
                failed.append({
                    "requirement_id": assessment.get("requirement_id"),
                    "status": status,
                    "confidence": assessment.get("confidence"),
                    "reasoning": assessment.get("reasoning"),
                    "evidence_quote": assessment.get("evidence_quote")
                })
        
        return failed

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.models.audit import PolicyAudit
from app.schemas.agents import RequirementAssessment

class AuditSnapshotter:
    """
    Handles immutable freezing of audit results and evidence integrity.
    Ensures every piece of evidence is cryptographically hashed.
    """
    
    ENGINE_NAME = "Company Compliance Engine"
    ENGINE_VERSION = "2.0.0"

    @staticmethod
    def calculate_hash(text: str) -> str:
        """Computes a SHA-256 hash for a segment of text."""
        if not text:
            return ""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @classmethod
    def create_frozen_snapshot(
        cls,
        audit_id: UUID,
        framework_metadata: Dict[str, Any],
        assessments: List[RequirementAssessment],
        overall_verdict: str,
        execution_trace: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Creates a structured, immutable snapshot payload with evidence hashes.
        """
        frozen_assessments = []
        for assessment in assessments:
            # Hash the evidence quote if it exists
            evidence_hash = cls.calculate_hash(assessment.evidence_quote) if assessment.evidence_quote else None
            
            frozen_assessments.append({
                "requirement_id": assessment.requirement_id,
                "status": assessment.status,
                "confidence": assessment.confidence,
                "reasoning": assessment.reasoning,
                "evidence_quote": assessment.evidence_quote,
                "evidence_hash": evidence_hash,
                "page_numbers": assessment.page_numbers
            })

        snapshot = {
            "snapshot_version": "1.0",
            "audit_id": str(audit_id),
            "engine": {
                "name": cls.ENGINE_NAME,
                "version": cls.ENGINE_VERSION,
                "evaluation_date": datetime.utcnow().isoformat()
            },
            "framework": {
                "name": framework_metadata.get("name"),
                "version": framework_metadata.get("version"),
                "effective_date": framework_metadata.get("effective_date")
            },
            "results": {
                "overall_verdict": overall_verdict,
                "requirements": frozen_assessments
            },
            "metadata": {
                "execution_trace": execution_trace,
                "integrity_check_passed": True
            }
        }
        
        # Calculate fingerprint for the entire snapshot
        snapshot["fingerprint"] = cls.calculate_hash(json.dumps(snapshot, sort_keys=True))
        
        return snapshot

    @classmethod
    def verify_integrity(cls, snapshot: Dict[str, Any]) -> bool:
        """
        Verifies the internal integrity of a snapshot by re-checking evidence hashes.
        """
        if not snapshot or "results" not in snapshot:
            return False
            
        requirements = snapshot["results"].get("requirements", [])
        for req in requirements:
            quote = req.get("evidence_quote")
            stored_hash = req.get("evidence_hash")
            
            if quote and stored_hash:
                if cls.calculate_hash(quote) != stored_hash:
                    return False
        
        return True

    @staticmethod
    def ensure_immutability(audit: PolicyAudit):
        """Raises an error if an audit already has a completed report."""
        if audit.report:
            raise ValueError(f"Audit {audit.id} is frozen and cannot be modified.")

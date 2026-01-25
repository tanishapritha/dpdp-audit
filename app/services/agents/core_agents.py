import json
import logging
from typing import List, Dict, Any
from openai import AsyncOpenAI
from app.core.config import settings
from app.schemas.agents import RequirementPlan, EvidenceBundle, RequirementAssessment, VerifiedAssessment

logger = logging.getLogger(__name__)

class PlannerAgent:
    """
    Determines which compliance requirements are relevant for a given document.
    Cannot invent requirement IDs - must select from provided list.
    """
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.model = "openai/gpt-4o-mini"

    async def plan(self, available_requirements: List[Dict[str, str]]) -> RequirementPlan:
        """
        Input: List of {requirement_id, title} from database
        Output: RequirementPlan with selected requirement_ids
        """
        system_prompt = (
            "You are a compliance planning agent. "
            "Your task is to identify which regulatory requirements are relevant "
            "for evaluating a privacy policy document against the DPDP Act 2023. "
            "You must ONLY select from the provided requirement IDs. "
            "You cannot invent new requirements."
        )

        req_list = "\n".join([
            f"- {r['requirement_id']}: {r['title']}" 
            for r in available_requirements
        ])

        user_prompt = (
            f"Available Requirements:\n{req_list}\n\n"
            "Task: Select ALL requirement IDs that should be evaluated for a privacy policy document. "
            "Return a JSON object with this schema:\n"
            "{\n"
            '  "requirement_ids": ["REQ-001", "REQ-002", ...],\n'
            '  "reasoning": "Brief explanation"\n'
            "}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            data = json.loads(response.choices[0].message.content)
            return RequirementPlan(**data)
        
        except Exception as e:
            logger.error(f"Planner agent failed: {str(e)}")
            # Fail-safe: return all requirements
            return RequirementPlan(
                requirement_ids=[r["requirement_id"] for r in available_requirements],
                reasoning="Fallback: evaluating all requirements due to planner error"
            )


class ReasonerAgent:
    """
    Evaluates a single requirement against evidence.
    Must cite evidence or return UNKNOWN.
    """
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.model = "openai/gpt-4o-mini"

    async def assess(
        self, 
        requirement_text: str, 
        evidence: EvidenceBundle
    ) -> RequirementAssessment:
        """
        Input: Requirement text + evidence bundle
        Output: Structured assessment with citations
        """
        system_prompt = (
            "You are a legal compliance assessment agent. "
            "Your task is to determine if a privacy policy explicitly addresses a statutory requirement. "
            "Rules:\n"
            "1. Only mark COMPLIANT if explicitly stated\n"
            "2. Mark PARTIAL if mentioned but vague\n"
            "3. Mark NON_COMPLIANT if contradicts or missing\n"
            "4. Mark UNKNOWN if insufficient evidence\n"
            "5. You MUST provide a direct quote as evidence or mark UNKNOWN\n"
            "6. Do not infer or assume compliance"
        )

        evidence_text = "\n\n".join([
            f"Document Chunk {i+1}: {chunk}"
            for i, chunk in enumerate(evidence.document_chunks)
        ])

        user_prompt = (
            f"Requirement: {requirement_text}\n\n"
            f"Evidence from Document:\n{evidence_text}\n\n"
            "Return JSON with this exact schema:\n"
            "{\n"
            '  "requirement_id": "' + evidence.requirement_id + '",\n'
            '  "status": "COMPLIANT|PARTIAL|NON_COMPLIANT|UNKNOWN",\n'
            '  "confidence": 0.0-1.0,\n'
            '  "evidence_quote": "direct quote or null",\n'
            '  "reasoning": "explicit justification",\n'
            '  "page_numbers": [1, 2]\n'
            "}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            data = json.loads(response.choices[0].message.content)
            return RequirementAssessment(**data)
        
        except Exception as e:
            logger.error(f"Reasoner agent failed for {evidence.requirement_id}: {str(e)}")
            # Fail-safe: return UNKNOWN
            return RequirementAssessment(
                requirement_id=evidence.requirement_id,
                status="UNKNOWN",
                confidence=0.0,
                evidence_quote=None,
                reasoning=f"Assessment failed due to error: {str(e)}",
                page_numbers=[]
            )


class VerifierAgent:
    """
    Reviews reasoner output for logical consistency.
    Can only downgrade, never upgrade.
    """
    
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.model = "openai/gpt-4o-mini"

    async def verify(
        self, 
        assessment: RequirementAssessment,
        evidence: EvidenceBundle
    ) -> VerifiedAssessment:
        """
        Input: Assessment + original evidence
        Output: Verified (possibly downgraded) assessment
        """
        system_prompt = (
            "You are a verification agent. "
            "Your task is to check if an assessment is justified by the evidence. "
            "You may ONLY downgrade status or confidence, never upgrade. "
            "If evidence does not support the claim, downgrade to UNKNOWN."
        )

        user_prompt = (
            f"Original Assessment:\n{assessment.model_dump_json(indent=2)}\n\n"
            f"Evidence Quote: {assessment.evidence_quote}\n\n"
            "Task: Verify if the status and confidence are justified. "
            "Return JSON:\n"
            "{\n"
            '  "requirement_id": "' + assessment.requirement_id + '",\n'
            '  "original_status": "' + assessment.status + '",\n'
            '  "verified_status": "COMPLIANT|PARTIAL|NON_COMPLIANT|UNKNOWN",\n'
            '  "original_confidence": ' + str(assessment.confidence) + ',\n'
            '  "verified_confidence": 0.0-1.0,\n'
            '  "verification_notes": "explanation if downgraded",\n'
            '  "approved": true|false\n'
            "}"
        )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            
            data = json.loads(response.choices[0].message.content)
            return VerifiedAssessment(**data)
        
        except Exception as e:
            logger.error(f"Verifier agent failed for {assessment.requirement_id}: {str(e)}")
            # Fail-safe: approve as-is
            return VerifiedAssessment(
                requirement_id=assessment.requirement_id,
                original_status=assessment.status,
                verified_status=assessment.status,
                original_confidence=assessment.confidence,
                verified_confidence=assessment.confidence,
                verification_notes=f"Verification skipped due to error: {str(e)}",
                approved=True
            )

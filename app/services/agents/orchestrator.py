import logging
from typing import List, Dict, Any
from datetime import datetime
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import LatencyTracker, ExecutionTracer
from app.models.compliance import ComplianceRequirement
from app.schemas.agents import RequirementAssessment, AgentOrchestrationResult
from app.services.agents.core_agents import PlannerAgent, ReasonerAgent, VerifierAgent
from app.services.agents.evidence_retriever import EvidenceRetriever

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Coordinates the agent pipeline for compliance evaluation.
    Ensures all agents operate within constraints.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE,
            default_headers={
                "HTTP-Referer": "https://compliance-engine.ai",
                "X-Title": "Company Compliance Engine",
            }
        )
        self.planner = PlannerAgent(self.client)
        self.reasoner = ReasonerAgent(self.client)
        self.verifier = VerifierAgent(self.client)
        self.retriever = EvidenceRetriever()
        self.latency_tracker = LatencyTracker()
        self.tracer = ExecutionTracer()

    async def evaluate_policy(
        self, 
        document_clauses: List[Dict[str, Any]]
    ) -> AgentOrchestrationResult:
        """
        Main orchestration method with observability.
        
        Pipeline:
        1. Load requirements from DB (source of truth)
        2. Plan which requirements to evaluate
        3. For each requirement:
           a. Retrieve evidence
           b. Reason about compliance
           c. Verify reasoning
        4. Aggregate verdict deterministically
        """
        
        # Step 1: Load requirements from database
        with self.latency_tracker.measure("load_requirements"):
            requirements = self._load_requirements()
            if not requirements:
                raise RuntimeError("No compliance requirements found in database")
        
        # Step 2: Plan evaluation
        with self.latency_tracker.measure("planner_agent"):
            plan = await self.planner.plan(requirements)
            logger.info(f"Planner selected {len(plan.requirement_ids)} requirements")
        
        # Validate all requirement_ids exist in database
        valid_ids = {r["requirement_id"] for r in requirements}
        invalid_ids = set(plan.requirement_ids) - valid_ids
        if invalid_ids:
            logger.warning(f"Planner returned invalid IDs: {invalid_ids}. Filtering them out.")
            plan.requirement_ids = [rid for rid in plan.requirement_ids if rid in valid_ids]
        
        # Step 3: Evaluate each requirement
        assessments = []
        for req_id in plan.requirement_ids:
            req_data = next((r for r in requirements if r["requirement_id"] == req_id), None)
            if not req_data:
                continue
            
            try:
                # 3a. Retrieve evidence
                with self.latency_tracker.measure(f"retrieval_{req_id}"):
                    evidence = self.retriever.retrieve(
                        requirement_id=req_id,
                        requirement_keywords=req_data.get("keywords", []),
                        document_clauses=document_clauses
                    )
                
                # 3b. Reason about compliance
                with self.latency_tracker.measure(f"reasoner_{req_id}"):
                    assessment = await self.reasoner.assess(
                        requirement_text=req_data["requirement_text"],
                        evidence=evidence
                    )
                
                # 3c. Verify reasoning
                with self.latency_tracker.measure(f"verifier_{req_id}"):
                    verification = await self.verifier.verify(assessment, evidence)
                
                # Record trace
                self.tracer.record_requirement_evaluation(
                    requirement_id=req_id,
                    evidence=evidence.model_dump(),
                    assessment=assessment.model_dump(),
                    verification=verification.model_dump()
                )
                
                # Use verified assessment
                if not verification.approved:
                    logger.info(f"Assessment for {req_id} was downgraded: {verification.verification_notes}")
                    assessment.status = verification.verified_status
                    assessment.confidence = verification.verified_confidence
                
                assessments.append(assessment)
                
            except Exception as e:
                logger.error(f"Failed to evaluate {req_id}: {str(e)}")
                # Add UNKNOWN assessment on failure
                assessments.append(RequirementAssessment(
                    requirement_id=req_id,
                    status="UNKNOWN",
                    confidence=0.0,
                    evidence_quote=None,
                    reasoning=f"Evaluation failed: {str(e)}",
                    page_numbers=[]
                ))
        
        # Step 4: Deterministic verdict aggregation
        overall_verdict = self._aggregate_verdict(assessments)
        
        # Capture final metrics
        total_latency = sum(self.latency_tracker.get_all_measurements().values())
        
        return AgentOrchestrationResult(
            assessments=assessments,
            overall_verdict=overall_verdict,
            metadata={
                "evaluated_at": datetime.utcnow().isoformat(),
                "total_requirements": len(requirements),
                "evaluated_requirements": len(assessments),
                "agent_version": "2.0",
                "total_latency_ms": total_latency,
                "latencies": self.latency_tracker.get_all_measurements(),
                "execution_trace": self.tracer.get_full_trace()
            }
        )

    def _load_requirements(self) -> List[Dict[str, Any]]:
        """
        Load all compliance requirements from database.
        Returns list of dicts with requirement metadata.
        """
        requirements = self.db.query(ComplianceRequirement).all()
        return [
            {
                "requirement_id": req.requirement_id,
                "title": req.title,
                "requirement_text": req.requirement_text,
                "risk_level": req.risk_level.value,
                "section_ref": req.section_ref,
                # Extract keywords from title for retrieval
                "keywords": req.title.lower().split()
            }
            for req in requirements
        ]

    def _aggregate_verdict(self, assessments: List[RequirementAssessment]) -> str:
        """
        Deterministic verdict logic (no AI).
        
        Rules:
        - If any NON_COMPLIANT → RED
        - Else if any PARTIAL → YELLOW
        - Else if any UNKNOWN → YELLOW
        - Else → GREEN
        """
        statuses = [a.status for a in assessments]
        
        if "NON_COMPLIANT" in statuses:
            return "RED"
        if "PARTIAL" in statuses or "UNKNOWN" in statuses:
            return "YELLOW"
        return "GREEN"

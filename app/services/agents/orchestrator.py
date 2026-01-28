import logging
import uuid
from uuid import UUID, uuid4
from typing import List, Dict, Any, Optional
from datetime import datetime
from openai import AsyncOpenAI
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.observability import LatencyTracker, ExecutionTracer
from app.models.compliance import ComplianceRequirement, ComplianceFramework
from app.schemas.agents import RequirementAssessment, AgentOrchestrationResult
from app.services.agents.core_agents import PlannerAgent, ReasonerAgent, VerifierAgent
from app.services.pdf_structured_processor import LayoutAwarePDFProcessor
from app.services.agents.hybrid_retriever import HybridRetriever
from app.models.document import DocumentChunk
from app.services.audit_snapshotter import AuditSnapshotter

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Coordinates the agent pipeline for compliance evaluation.
    Upgraded: Layout-aware extraction + Hybrid Semantic Search.
    """
    
    def __init__(self, db: Session, audit_id: Optional[UUID] = None):
        self.db = db
        self.audit_id = audit_id or uuid4()
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
        self.retriever = HybridRetriever(self.db)
        self.latency_tracker = LatencyTracker()
        self.tracer = ExecutionTracer()

    async def ingest_and_evaluate(self, file_path: str) -> AgentOrchestrationResult:
        """
        New Entry Point: Handles structured ingestion then evaluation.
        """
        # 1. Advanced PDF Parsing
        with self.latency_tracker.measure("layout_aware_extraction"):
            processor = LayoutAwarePDFProcessor()
            structured_content = processor.extract_structured_text(file_path)
            chunks = processor.create_semantic_chunks(structured_content)
            
        # 2. Embedding & Storage (Scalable Retrieval)
        with self.latency_tracker.measure("semantic_indexing"):
            retriever = HybridRetriever(self.db)
            for i, chunk in enumerate(chunks):
                embedding = retriever._get_embedding(chunk["text"])
                db_chunk = DocumentChunk(
                    audit_id=self.audit_id,
                    chunk_index=i,
                    text=chunk["text"],
                    section_context=chunk.get("section_context"),
                    page_number=chunk["pages"][0] if chunk["pages"] else 1,
                    embedding=embedding
                )
                self.db.add(db_chunk)
            self.db.commit()

        # 3. Proceed to Evaluation using Hybrid Retrieval
        return await self.evaluate_policy(query_context="General Compliance")

    async def evaluate_policy(
        self, 
        query_context: str = ""
    ) -> AgentOrchestrationResult:
        """
        Main orchestration method with observability and hybrid retrieval.
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
        
        # Validate all requirement_ids
        valid_ids = {r["requirement_id"] for r in requirements}
        plan.requirement_ids = [rid for rid in plan.requirement_ids if rid in valid_ids]
        
        # Step 3: Evaluate each requirement
        assessments = []
        for req_id in plan.requirement_ids:
            req_data = next((r for r in requirements if r["requirement_id"] == req_id), None)
            if not req_data:
                continue
            
            try:
                # 3a. Hybrid Semantic Retrieval (Real RAG)
                with self.latency_tracker.measure(f"hybrid_retrieval_{req_id}"):
                    evidence = self.retriever.retrieve(
                        audit_id=self.audit_id,
                        requirement_id=req_id,
                        query=f"{req_data['title']} {req_data['requirement_text']}"
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
                
                # Record trace and use verified status
                self.tracer.record_requirement_evaluation(
                    requirement_id=req_id,
                    evidence=evidence.model_dump(),
                    assessment=assessment.model_dump(),
                    verification=verification.model_dump()
                )
                
                if not verification.approved:
                    assessment.status = verification.verified_status
                    assessment.confidence = verification.verified_confidence
                
                assessments.append(assessment)
                
            except Exception as e:
                logger.error(f"Failed to evaluate {req_id}: {str(e)}")
                assessments.append(RequirementAssessment(
                    requirement_id=req_id, status="UNKNOWN", confidence=0.0,
                    evidence_quote=None, reasoning=f"Evaluation failed: {str(e)}", page_numbers=[]
                ))
        
        # Step 4: Deterministic verdict aggregation
        overall_verdict = self._aggregate_verdict(assessments)
        
        # Capture final metrics
        total_latency = sum(self.latency_tracker.get_all_measurements().values())
        execution_trace = self.tracer.get_full_trace()
        
        # Step 5: Freeze Snapshot (Audit Defensibility)
        # We pick the framework associated with requirements
        framework_metadata = {"name": "Multi-Framework Evaluation", "version": "Combined", "effective_date": datetime.utcnow().date().isoformat()}
        if requirements:
            # Try to get the first actual framework from the DB for metadata
            fw = self.db.query(ComplianceFramework).first()
            if fw:
                framework_metadata = {
                    "name": fw.name,
                    "version": fw.version,
                    "effective_date": fw.effective_date.isoformat()
                }

        frozen_report = AuditSnapshotter.create_frozen_snapshot(
            audit_id=self.audit_id or "00000000-0000-0000-0000-000000000000",
            framework_metadata=framework_metadata,
            assessments=assessments,
            overall_verdict=overall_verdict,
            execution_trace=execution_trace
        )
        
        return AgentOrchestrationResult(
            assessments=assessments,
            overall_verdict=overall_verdict,
            metadata=frozen_report
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

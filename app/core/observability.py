import time
import logging
from typing import Any, Dict, Optional
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class LatencyTracker:
    """Tracks execution latency for agents and operations."""
    
    def __init__(self):
        self.measurements: Dict[str, float] = {}
    
    @contextmanager
    def measure(self, operation_name: str):
        """Context manager to measure operation latency."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.measurements[operation_name] = duration_ms
            logger.info(f"{operation_name} completed in {duration_ms:.2f}ms")
    
    def get_measurement(self, operation_name: str) -> Optional[float]:
        """Get latency measurement for an operation."""
        return self.measurements.get(operation_name)
    
    def get_all_measurements(self) -> Dict[str, float]:
        """Get all latency measurements."""
        return self.measurements.copy()
    
    def reset(self):
        """Clear all measurements."""
        self.measurements.clear()


class ExecutionTracer:
    """Captures structured execution traces for audit operations."""
    
    def __init__(self):
        self.traces: Dict[str, Any] = {}
        self.latency_tracker = LatencyTracker()
    
    def record_agent_execution(
        self,
        agent_name: str,
        input_data: Dict[str, Any],
        output_data: Dict[str, Any],
        duration_ms: float,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Record execution details for a single agent."""
        trace = {
            "agent_name": agent_name,
            "started_at": datetime.utcnow().isoformat(),
            "duration_ms": duration_ms,
            "input_summary": self._summarize_data(input_data),
            "output_summary": self._summarize_data(output_data),
            "success": success,
            "error": error
        }
        
        if agent_name not in self.traces:
            self.traces[agent_name] = []
        self.traces[agent_name].append(trace)
        
        logger.debug(f"Recorded trace for {agent_name}: {trace}")
    
    def record_requirement_evaluation(
        self,
        requirement_id: str,
        evidence: Dict[str, Any],
        assessment: Dict[str, Any],
        verification: Dict[str, Any]
    ):
        """Record complete evaluation trace for a requirement."""
        trace = {
            "requirement_id": requirement_id,
            "evidence_chunks": len(evidence.get("document_chunks", [])),
            "assessment_status": assessment.get("status"),
            "assessment_confidence": assessment.get("confidence"),
            "verified_status": verification.get("verified_status"),
            "verified_confidence": verification.get("verified_confidence"),
            "was_downgraded": verification.get("verified_status") != assessment.get("status")
        }
        
        if "requirement_evaluations" not in self.traces:
            self.traces["requirement_evaluations"] = []
        self.traces["requirement_evaluations"].append(trace)
    
    def get_full_trace(self) -> Dict[str, Any]:
        """Get complete execution trace."""
        return {
            "traces": self.traces,
            "latencies": self.latency_tracker.get_all_measurements(),
            "captured_at": datetime.utcnow().isoformat()
        }
    
    def _summarize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a summary of data for tracing (avoid storing large payloads)."""
        summary = {}
        for key, value in data.items():
            if isinstance(value, list):
                summary[key] = f"<list of {len(value)} items>"
            elif isinstance(value, str) and len(value) > 100:
                summary[key] = f"<string of {len(value)} chars>"
            else:
                summary[key] = value
        return summary

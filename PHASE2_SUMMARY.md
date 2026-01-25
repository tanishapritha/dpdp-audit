# Phase 2 Agent-Based Compliance Intelligence - Implementation Summary

## Overview
Phase 2 introduces a modular, agent-based evaluation system that operates strictly within the compliance framework established in Phase 1.

## Core Principles Maintained
✅ Database is source of truth for requirements  
✅ AI cannot invent requirements  
✅ Final verdict is deterministic code  
✅ All outputs are validated against Pydantic schemas  
✅ Invalid AI outputs are discarded, not corrected  
✅ API contracts unchanged  

## Architecture

### Agent Pipeline
```
1. PlannerAgent → Selects relevant requirement_ids from DB
2. EvidenceRetriever → Retrieves document chunks (deterministic)
3. ReasonerAgent → Assesses compliance per requirement
4. VerifierAgent → Validates/downgrades assessments
5. Orchestrator → Aggregates deterministic verdict
```

### New Components

**Schemas** (`app/schemas/agents.py`)
- `RequirementPlan`: Planner output
- `EvidenceBundle`: Retrieved evidence
- `RequirementAssessment`: Per-requirement evaluation
- `VerifiedAssessment`: Verified output
- `AgentOrchestrationResult`: Final pipeline output

**Agents** (`app/services/agents/`)
- `core_agents.py`: PlannerAgent, ReasonerAgent, VerifierAgent
- `evidence_retriever.py`: Deterministic keyword-based retrieval
- `orchestrator.py`: Pipeline coordination with validation

**Configuration**
- `USE_AGENT_BASED_EVALUATION`: Boolean flag in config.py
- Routes to agent system when True, legacy system when False

## Validation Guardrails

1. **Requirement ID Validation**
   - Planner output filtered against DB requirement_ids
   - Invalid IDs logged and discarded

2. **Schema Validation**
   - All agent outputs validated via Pydantic
   - Malformed JSON triggers fallback to UNKNOWN status

3. **Verification Layer**
   - VerifierAgent can only downgrade, never upgrade
   - Unjustified confidence scores are reduced

4. **Deterministic Verdict**
   - Aggregation logic in code, not AI
   - Rules: NON_COMPLIANT → RED, PARTIAL/UNKNOWN → YELLOW, else GREEN

## API Compatibility

The agent system produces output in the same format as the legacy system:
```json
{
  "overall_verdict": "RED|YELLOW|GREEN",
  "requirements": [
    {
      "requirement_id": "DPDP_6_1",
      "status": "COMPLIANT|PARTIAL|NON_COMPLIANT|UNKNOWN",
      "reason": "...",
      "evidence": ["quote"],
      "page_numbers": [1, 2]
    }
  ]
}
```

No changes to:
- API endpoints
- Response schemas
- Database writes
- Frontend contracts

## Configuration

To enable agent-based evaluation:
```bash
# In .env
USE_AGENT_BASED_EVALUATION=true
```

To revert to legacy:
```bash
USE_AGENT_BASED_EVALUATION=false
```

## Error Handling

All agents have fail-safe behavior:
- **Planner fails** → Evaluate all requirements
- **Reasoner fails** → Return UNKNOWN status
- **Verifier fails** → Approve original assessment
- **Orchestrator fails** → Audit marked as FAILED

## Auditability Improvements

1. **Structured Reasoning**: Each assessment includes explicit reasoning field
2. **Evidence Citations**: Direct quotes from documents
3. **Verification Trail**: Original vs verified status tracked
4. **Metadata**: Timestamps, agent versions, requirement counts

## Testing Considerations

Existing tests remain valid. Agent-specific tests should verify:
- Requirement ID validation
- Schema conformance
- Fallback behavior
- Deterministic verdict logic

## Future-Proofing

The agent architecture supports:
- Additional agent roles (e.g., SummaryAgent)
- Multi-framework evaluation (GDPR, CCPA)
- Advanced retrieval strategies
- Human-in-the-loop workflows

All without breaking current contracts.

## Migration Notes

- Existing audits use legacy format (preserved)
- New audits use agent system (if enabled)
- Both systems write identical report structure
- No data migration required

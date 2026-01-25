# Company Compliance Engine - Implementation Complete

## Overview
A production-ready compliance auditing system that evaluates privacy policies against the Digital Personal Data Protection (DPDP) Act, 2023.

## Architecture

### Database Layer (PostgreSQL)
- UUID-based primary keys across all tables
- JSONB for extensible report storage
- Compliance framework models with foreign key integrity
- Automatic seeding of DPDP requirements on startup

### Agent-Based Evaluation Pipeline
1. **Planner Agent** - Selects relevant requirements from database
2. **Evidence Retriever** - Keyword-based document chunk retrieval
3. **Reasoner Agent** - Per-requirement compliance assessment
4. **Verifier Agent** - Validates and potentially downgrades assessments
5. **Orchestrator** - Coordinates pipeline with deterministic verdict logic

### Observability & Trust
- **Latency Tracking**: Measures execution time for each agent and operation
- **Execution Tracing**: Captures structured traces of all evaluation steps
- **Explainability Helpers**: Internal utilities for debugging decisions
- **Failure Transparency**: Graceful degradation with UNKNOWN status on errors

## Key Design Principles

### Determinism
- Final verdicts computed by code logic, not AI
- Verdict rules: NON_COMPLIANT → RED, PARTIAL/UNKNOWN → YELLOW, ALL COMPLIANT → GREEN
- All AI outputs validated against Pydantic schemas

### Safety Guardrails
- AI cannot invent requirement IDs (validated against database)
- Verifier can only downgrade, never upgrade assessments
- Missing evidence defaults to UNKNOWN status
- Invalid AI outputs are discarded, not corrected

### Auditability
- All requirements loaded from database (single source of truth)
- Every assessment includes explicit reasoning and evidence citations
- Complete execution traces stored in metadata
- Per-requirement and per-agent latency metrics captured

## API Endpoints

### Authentication
- `POST /api/v1/login/access-token` - Generate JWT token
- `GET /api/v1/me` - Get current user details

### Compliance Evaluation
- `POST /api/v1/upload` - Upload PDF policy for analysis
- `GET /api/v1/{policy_id}/status` - Poll evaluation progress
- `GET /api/v1/{policy_id}/report` - Retrieve final compliance report

## Configuration

### Environment Variables
```bash
PROJECT_NAME="Company Compliance Engine"
SQLALCHEMY_DATABASE_URL="postgresql://user:pass@localhost:5432/db"
OPENAI_API_KEY="sk-..."
OPENAI_API_BASE="https://openrouter.ai/api/v1"
SECRET_KEY="your-secret-key"
USE_AGENT_BASED_EVALUATION=true  # Toggle agent vs legacy system
```

### Toggle Between Systems
- Set `USE_AGENT_BASED_EVALUATION=true` for agent-based evaluation
- Set `USE_AGENT_BASED_EVALUATION=false` for legacy evaluation
- Both systems produce identical API response formats

## Testing

### Critical Test Suite
Six essential tests prove system safety:
1. Agent pipeline end-to-end functionality
2. Requirement ID enforcement (no AI invention)
3. Missing evidence → UNKNOWN status
4. Verifier never upgrades (only downgrades)
5. Deterministic verdict without AI
6. Configuration routing isolation

Run tests:
```bash
pytest tests/
```

## Data Models

### Compliance Framework
- Stores regulatory framework metadata (DPDP 2023)
- Seeded automatically from `compliance/dpdp/dpdp_2023_requirements.json`
- Extensible to additional frameworks (GDPR, CCPA, etc.)

### Compliance Requirements
- 14 DPDP statutory requirements
- Each with requirement ID, section reference, risk level, and full text
- Used as source of truth for all evaluations

### Policy Audits
- Tracks evaluation status (PENDING → EXTRACTING → ANALYZING → COMPLETED)
- Stores final report as JSONB
- Includes RAGAS faithfulness and relevancy metrics

## Observability Features

### Latency Metrics
Captured for each operation:
- Requirement loading
- Planner execution
- Evidence retrieval per requirement
- Reasoner execution per requirement
- Verifier execution per requirement
- Total evaluation time

### Execution Traces
Complete audit trail includes:
- Planner selected requirement IDs
- Evidence bundles retrieved
- Reasoner assessments
- Verifier decisions
- Downgrades and confidence adjustments

### Explainability (Internal)
Helper functions for debugging:
- `explain_requirement_status()` - Why was this requirement marked X?
- `explain_verdict()` - How was the final verdict determined?
- `get_evidence_chain()` - What evidence was used?
- `list_failed_requirements()` - Which requirements failed?

## Security

- JWT-based authentication with bcrypt password hashing
- User isolation: users can only access their own audits
- Role-based access control (USER, ADMIN) in place for future expansion
- CORS configured (currently permissive for MVP)

## Deployment

### Database Setup
```bash
# Create PostgreSQL database
createdb compliance_db

# Update .env
SQLALCHEMY_DATABASE_URL="postgresql://user:pass@localhost:5432/compliance_db"

# Run application (auto-seeds requirements)
uvicorn app.main:app --reload
```

### Verify Startup
On successful startup:
```
✓ Compliance framework initialized successfully
```

## Future Extensibility

The architecture supports:
- Additional compliance frameworks (GDPR, CCPA)
- Advanced retrieval strategies (vector search)
- Human-in-the-loop workflows
- Multi-language policy analysis
- Real-time streaming evaluations

All without breaking existing API contracts.

## Technical Stack

- **Framework**: FastAPI + SQLAlchemy 2.0
- **Database**: PostgreSQL with UUID and JSONB
- **AI**: OpenAI/OpenRouter (gpt-4o-mini)
- **PDF Processing**: pdfplumber
- **Quality Metrics**: RAGAS (faithfulness, answer relevancy)
- **Testing**: pytest with async support
- **Authentication**: JWT with OAuth2

## Repository Structure
```
BACKEND/
├── app/
│   ├── api/v1/endpoints/    # API routes
│   ├── core/                # Config, database, security
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   └── services/
│       ├── agents/          # Agent-based evaluation
│       ├── compliance_engine.py  # Legacy evaluation
│       ├── llm_service.py
│       ├── pdf_processor.py
│       └── ragas_evaluator.py
├── compliance/dpdp/         # DPDP requirements data
├── tests/                   # Test suite
└── requirements.txt
```

## Status

✅ Phase 1: PostgreSQL migration with UUID and compliance models  
✅ Phase 2: Agent-based evaluation with strict validation  
✅ Phase 3: Observability, tracing, and explainability  

**System is production-ready for deployment.**

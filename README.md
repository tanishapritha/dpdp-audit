# Company Compliance Engine - Implementation Complete

## Overview
A production-ready compliance auditing system that evaluates privacy policies against regulatory frameworks like the Digital Personal Data Protection (DPDP) Act, 2023 and GDPR.

## Architecture

### Database Layer (PostgreSQL)
- **Hybrid Search**: `PgVector` integration for semantic vector retrieval.
- **Identity**: UUID-based primary keys across all tables.
- **Reporting**: JSONB for extensible, structured report storage.
- **Multi-Framework**: Support for DPDP and GDPR-Lite seeded from JSON data.

### Production-Grade RAG Pipeline
1. **Layout-Aware Extraction**: Uses `PyMuPDF` to identify headers, articles, and section hierarchy.
2. **Semantic Context Retrieval**: Context-aware chunking (1500 chars) preserving parent section metadata.
3. **Hybrid Search**: Combines semantic vector similarity (OpenAI embeddings) with keyword boosting.
4. **4-Agent Pipeline**:
    - **Planner**: Selects relevant regulatory requirements.
    - **Hybrid Retriever**: Fetches evidence from the indexed document.
    - **Reasoner**: Performs deep compliance assessment with citations.
    - **Verifier**: Hard-coded safety agent that can only downgrade confidence/status.

### Audit Defensibility & Trust
- **Evidence Hashes**: Every evidence quote is SHA-256 hashed during evaluation.
- **Immutable Snapshots**: Reports are frozen with a cryptographic fingerprint after completion.
- **Tamper Detection**: Verification logic that invalidates snapshots if evidence is modified.
- **Explainability**: Internal utilities to trace the exact reasoning path of the agents.
- **Observability**: Nano-second precision latency tracking for every agent operation.

## Design Principles

### Determinism
- Final compliance verdicts (RED/YELLOW/GREEN) computed by code logic, not AI.
- AI outputs are strictly constrained by Pydantic contracts.

### Safety Guardrails
- **Verifier Constraint**: AI can never "upgrade" compliance; it can only verify or flag as unknown.
- **Requirement Enforcement**: AI is prevented from inventing or hallucinating requirement IDs.
- **Failure Transparency**: Any pipeline error results in a graceful `UNKNOWN` state.

## API Endpoints

### Authentication
- `POST /api/v1/login/access-token` - Generate JWT token
- `GET /api/v1/me` - Get current user details

### Compliance Evaluation
- `POST /api/v1/upload` - Upload PDF policy for layout-aware indexing and multi-agent analysis.
- `GET /api/v1/{policy_id}/status` - Poll evaluation and indexing progress.
- `GET /api/v1/{policy_id}/report` - Retrieve frozen compliance report with cryptographic proof.

## Key Features

### Multi-Framework Support
The system treats laws as data. It automatically discovers and seeds frameworks from the `compliance/` directory.

### Professional Export
- **JSON Export**: Full machine-readable trace with hashes and fingerprints.
- **PDF Export**: Human-friendly audit report with color-coded verdicts and evidence citations.

## Technical Stack
- **Framework**: FastAPI + SQLAlchemy 2.0
- **Database**: PostgreSQL + PgVector
- **AI**: OpenAI/OpenRouter (gpt-4o-mini + text-embedding-3-small)
- **PDF**: PyMuPDF (Fitz)
- **Security**: SHA-256 Hashing + JWT + Bcrypt
- **Testing**: Pytest (Async)

## Status
✅ Phase 1: PostgreSQL migration with UUID and compliance models  
✅ Phase 2: Multi-agent reasoning pipeline  
✅ Phase 3: Observability, tracing, and explainability  
✅ Phase 4: Audit Defensibility (Freezing/Hashing) + Hybrid RAG (PgVector)

**System is production-ready for audit and deployment.**

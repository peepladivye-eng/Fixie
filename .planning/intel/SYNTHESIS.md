# Synthesis Summary

## Document Breakdown
Total documents ingested: 8
- ADR: 1 (`AGENTS.md`)
- SPEC: 6 (`contracts/interfaces.md`, `prompts/antigravity/01_ui_run_view.md`, `prompts/antigravity/02_ui_pages.md`, `prompts/antigravity/03_backend_foundation.md`, `prompts/antigravity/04_backend_agent.md`, `prompts/antigravity/05_smoke.md`)
- PRD: 1 (`README.md`)
- DOC: 0
- UNKNOWN: 0

## Extracted Intel
- **Decisions Locked**: 14 locked architectural decisions (`.planning/intel/decisions.md`)
  - Stack constraints (Python 3.12, FastAPI, SQLite, Next.js 15, React 19, Tailwind v4)
  - Frozen contract boundaries
  - Zero live API calls / fake-first testing rule
  - Multi-agent lane isolation & branch ownership
  - Deterministic candidate patch scoring
  - Persistent budget & call guards
- **Requirements**: 6 product requirements (`.planning/intel/requirements.md`)
  - `REQ-triage-ingest`: Issue report ingestion and triage
  - `REQ-reproduction-sandbox`: Bug reproduction in container sandbox
  - `REQ-speculative-branching`: Sandbox checkpointing and K-way parallel candidate branching
  - `REQ-parallel-verification`: Concurrent test suite execution and early competitor cancellation
  - `REQ-winner-selection-delivery`: Deterministic candidate ranking, unified diff generation, and PR delivery
  - `REQ-live-observability`: Real-time SSE event streaming, timeline, ANSI terminal, and @xyflow/react branch graph
- **Constraints**: 11 technical constraints (`.planning/intel/constraints.md`)
  - 4 API contracts (LLM, Search, GitHub, OpenAPI)
  - 2 protocols (Sandbox lifecycle, Agent loop orchestration)
  - 1 data schema (Event streaming protocol)
  - 4 non-functional / architectural guidelines (UI run view, UI pages, Backend foundation, Smoke runner)
- **Context Topics**: 3 operational topics (`.planning/intel/context.md`)
  - Hackathon scope and objectives
  - Centralized verification & testing rules
  - Multi-agent execution sequence and dependencies

## Conflict Analysis
- **Blockers**: 0
- **Competing Variants**: 0
- **Auto-resolved / Informational**: 3
- Detailed conflict report: `.planning/INGEST-CONFLICTS.md`

## Per-Type Intel Pointers
- Decisions: `.planning/intel/decisions.md`
- Requirements: `.planning/intel/requirements.md`
- Constraints: `.planning/intel/constraints.md`
- Context: `.planning/intel/context.md`

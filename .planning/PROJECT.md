# Fixie

## What This Is

Fixie is an autonomous bug reproduction and speculative patch engine built for the Nebius x NVIDIA Global AI Hackathon (Track 1: Coding and Agentic Engineering). It takes a GitHub issue or benchmark instance, reproduces the bug in an isolated container sandbox, forks the sandbox state into K candidate patches evaluated in parallel, deterministically scores them, and delivers a unified diff, test evidence, and a GitHub pull request. The entire run lifecycle is streamed live into a dark-mode web dashboard featuring a step timeline, an ANSI terminal, and an interactive branch tree.

## Core Value

Automated speculative patch branching evaluated in parallel sandboxes with deterministic scoring and live streaming observability.

## Business Context

- **Customer**: Software engineering teams, autonomous coding agent platforms, and automated CI/CD remediation pipelines.
- **Success metric**: Resolve rate on benchmark bug fixtures and cost-per-fix below $0.08 budget target.
- **Track**: Nebius x NVIDIA Global AI Hackathon, Track 1 (Coding and Agentic Engineering).

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] **REQ-triage-ingest**: Ingest GitHub issues and benchmark instances with AST-based context selection.
- [ ] **REQ-reproduction-sandbox**: Spin up container sandboxes, execute reproduction commands, and record compact failure summaries.
- [ ] **REQ-speculative-branching**: Checkpoint sandbox state and fork into K candidate branches with distinct prompt strategies concurrently.
- [ ] **REQ-parallel-verification**: Execute verification test suites across all candidates simultaneously via asyncio.gather and cancel competitors on clean pass.
- [ ] **REQ-winner-selection-delivery**: Deterministically score candidates (pass count, regression minimization, diff brevity, duration), package diffs, and open PRs.
- [ ] **REQ-live-observability**: Real-time SSE streaming into web dashboard featuring step timeline, ANSI terminal, and @xyflow/react branch graph.

### Out of Scope

- Live paid API calls during development — all development and automated testing must use fake providers or cassette replay.
- Editing frozen contract files (`contracts/events.schema.json`, `contracts/openapi.yaml`, `contracts/interfaces.md`) without formal change requests.
- Model-based patch ranking or subjective scoring — scoring must be deterministic code only.
- Exposing hidden benchmark tests to the agent or copying them into working sandboxes.

## Context

- **Backend Architecture**: Python 3.12, FastAPI, httpx (async only), pydantic, SQLite persistence and response caching.
- **Frontend Architecture**: Next.js 15 App Router, React 19, TypeScript, Tailwind v4, shadcn/ui, motion/react, @xyflow/react, cmdk, recharts.
- **Observability Protocol**: Server-Sent Events (SSE) with Last-Event-ID reconnection semantics and normalized event schemas.
- **Cost Controls**: SQLite-persisted budget guards (HARD_CAP_USD, CALL_CAP, RUN_BUDGET_USD).

## Constraints

- **Security**: Never read, print, log, or commit `.env`. All configuration is derived from environment variables.
- **Testing**: Zero live API calls during development. In-process clients and `scripts/check.py` drive verification.
- **Modularity**: Files must remain under ~300 lines; imports use `backend/` as root (`app.*`).
- **Styling**: All frontend colors must derive strictly from `frontend/styles/tokens.css`.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Frozen Interface Contracts | Enforces clean separation between backend agent, API, and frontend run view | ✓ Locked |
| Speculative Parallel Branching | Explores multiple patch strategies simultaneously to optimize fix rates | ✓ Locked |
| Deterministic Code Scoring | Eliminates LLM evaluation drift and hallucinated benchmarks | ✓ Locked |
| Offline Fake/Cassette First | Zero API cost during development and test suite runs | ✓ Locked |
| Strict Multi-Agent Lane Ownership | Enables independent, conflict-free parallel implementation | ✓ Locked |
| Persistent Budget Guards | Prevents unbounded LLM spend and runaway container execution | ✓ Locked |
| Hidden Test Anti-Leakage | Ensures benchmark evaluation validity by isolating grading tests | ✓ Locked |

---
*Last updated: 2026-10-29 after doc ingest*

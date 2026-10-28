# Roadmap: Fixie

## Overview

Fixie is built in targeted stages matching the multi-agent lane architecture. We first establish the solid core backend infrastructure and contracts (FastAPI, async LLM client, sandbox protocols, replay engines, and persistent budget guards). In parallel, the frontend run view and dashboard pages are constructed against frozen schemas and recorded event streams. Once the foundation is merged, the speculative branching agent pipeline is integrated, culminating in end-to-end benchmark evaluation and live provider smoke verification.

## Phases

- [ ] **Phase 1: Backend Foundation** - Async LLM client, sandbox interface, SSE replay streaming, and persistent cost limiters.
- [ ] **Phase 2: Frontend Run View** - Real-time SSE streaming client, timeline progression, ANSI terminal, and @xyflow/react branch tree.
- [ ] **Phase 3: Frontend Pages & Navigation** - Home explorer, evaluation dashboard with Recharts, shared empty/error states, and command palette.
- [ ] **Phase 4: Backend Agent Pipeline** - AST context selection, reproduction sandbox checks, parallel K-way candidate branching, deterministic scoring, and evaluation harness.
- [ ] **Phase 5: Smoke Runner & Live Verification** - Owner smoke test script for Nebius/NVIDIA LLMs and Contree-SDK container sandboxes.

## Phase Details

### Phase 1: Backend Foundation
**Goal**: Build the core backend runtime, asynchronous LLM tier router, sandbox session protocol, event replay endpoints, and SQLite budget guards.  
**Depends on**: Nothing (first phase)  
**Requirements**: [SANDBOX-01, SANDBOX-04]  
**Success Criteria** (what must be TRUE):
  1. FastAPI server boots asynchronously on port 8000 and serves OpenAPI contract endpoints.
  2. `POST /runs` accepts fixtures, issue URLs, and showcase runs, returning 201 with a valid run ID.
  3. `GET /runs/{id}/events` replays `sample_run.jsonl` events matching `events.schema.json` with clean SSE connection handling.
  4. LLM client supports asynchronous calls, role-to-tier mappings (`lightning`, `super`, `ultra`), response caching, and cassette replay without network calls.
  5. SQLite stores budget counters (`HARD_CAP_USD`, `CALL_CAP`, `RUN_BUDGET_USD`) surviving server restarts.
**Plans**: 3 plans

Plans:
- [ ] 01-01: Implement async LLM provider with tier routing, models.json catalog, response cache, and cassette storage.
- [ ] 01-02: Implement Sandbox protocol, LocalSandbox runtime, and async execution wrappers.
- [ ] 01-03: Implement FastAPI routes (POST /runs, GET /runs/{id}, SSE streaming, GET /showcase) and SQLite persistent limiters.

### Phase 2: Frontend Run View
**Goal**: Construct the real-time observability interface displaying the 5-step lifecycle, live terminal output, and interactive branch graph.  
**Depends on**: Phase 1 contracts (operates independently against sample replays)  
**Requirements**: [UI-01, UI-02, UI-03]  
**Success Criteria** (what must be TRUE):
  1. Pure event reducer `foldEvent` processes all contract event types, tracking steps, branches, logs, winner, and cost splits.
  2. ReplaySource plays `sample_run.jsonl` at 1x, 2x, and 4x speeds with pause/resume functionality.
  3. Desktop view presents a synchronized 3-column layout (Timeline, ANSI terminal, @xyflow/react branch tree) collapsing gracefully to tabs on mobile.
  4. Candidate branch nodes animate smoothly with state color cues (pulse running, green pass, red fail, dimmed cancel, glowing winner).
  5. Bottom meter displays live animated dollar and duration counters with tier breakdowns.
**Plans**: 2 plans

Plans:
- [ ] 02-01: Build TypeScript event types, `foldEvent` state reducer with unit tests, and Replay/Live source abstractions.
- [ ] 02-02: Implement `/run/[id]` page with step timeline, ANSI log viewer, animated @xyflow/react branch tree, and result panels.

### Phase 3: Frontend Pages & Navigation
**Goal**: Implement the home page, evaluation metrics dashboard, shared application states, and quick-jump command palette.  
**Depends on**: Phase 1 & 2 contracts  
**Requirements**: [UI-04]  
**Success Criteria** (what must be TRUE):
  1. Home page renders headline, issue URL input, showcase chips, and Replay/Live mode switch.
  2. `/eval` page visualizes baseline vs branching resolve rates and cost per fix using Recharts, with prominent synthetic data badges.
  3. Shared state components render calm error, rate-limited, loading skeleton, and waking-up states.
  4. Command palette (cmdk, Ctrl/Cmd+K) allows keyboard navigation between showcase runs and pages.
**Plans**: 2 plans

Plans:
- [ ] 03-01: Build home page with showcase cards, hero effects, and command palette navigation.
- [ ] 03-02: Implement `/eval` dashboard with Recharts visualizations, per-instance fixture tables, and fallback states.

### Phase 4: Backend Agent Pipeline
**Goal**: Implement the autonomous agent loop: intelligent context extraction, reproduction verification, parallel candidate branching, and deterministic scoring.  
**Depends on**: Phase 1  
**Requirements**: [TRIAGE-01, TRIAGE-02, TRIAGE-03, SANDBOX-02, SANDBOX-03, BRANCH-01, BRANCH-02, BRANCH-03, VERIFY-01, VERIFY-02, VERIFY-03, VERIFY-04, DELIVER-01, DELIVER-02, DELIVER-03]  
**Success Criteria** (what must be TRUE):
  1. Context selection extracts relevant functions and classes using AST analysis and grep, bounded by role token limits.
  2. Reproduction step captures compact failure summaries and aborts early if the test passes unexpectedly.
  3. Speculative branching forks K candidate sandboxes in parallel (`asyncio.gather`) using distinct prompt strategies.
  4. Competitor branches are cancelled immediately once a candidate passes all tests with zero regressions.
  5. Scoring algorithm deterministically ranks patches based on test passing, diff brevity, and runtime.
  6. Evaluation runner executes benchmark instances in fresh sandboxes with hidden test grading.
**Plans**: 3 plans

Plans:
- [ ] 04-01: Implement AST context extraction, compact test failure parsing, and reproduction checkpointing.
- [ ] 04-02: Implement speculative candidate branching, parallel execution loop, deterministic scoring, and task cancellation.
- [ ] 04-03: Implement delivery packaging, GitHub PR creation, and benchmark evaluation harness.

### Phase 5: Smoke Runner & Live Verification
**Goal**: Build the repository owner's smoke testing suite for validating live provider keys and remote container sandboxes.  
**Depends on**: Phase 1 & Phase 4  
**Requirements**: [SANDBOX-01, VERIFY-01]  
**Success Criteria** (what must be TRUE):
  1. `backend/tools/smoke.py` validates Nemotron model connectivity on Nebius and NVIDIA NIM endpoints.
  2. Contree-SDK container sandboxes launch, execute basic Python commands, and verify outbound network connectivity.
  3. Live container forks execute three concurrent tasks via `asyncio.gather` and report timing benchmarks.
  4. Summary table outputs PASS/FAIL verdicts with total API spend staying under a few cents.
**Plans**: 1 plan

Plans:
- [ ] 05-01: Implement `backend/tools/smoke.py` and requirements-smoke.txt with live provider validation checks.

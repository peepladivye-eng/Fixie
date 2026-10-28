# Requirements: Fixie

**Defined:** 2026-10-29  
**Core Value:** Automated speculative patch branching evaluated in parallel sandboxes with deterministic scoring and live streaming observability.

## v1 Requirements

### Triage & Ingestion

- [ ] **TRIAGE-01**: Ingest issue data from GitHub issue URLs, local benchmark fixtures, or JSON test instances.
- [ ] **TRIAGE-02**: Select relevant context files and functions using AST extraction and grep, strictly capped by model input limits.
- [ ] **TRIAGE-03**: Return up to 8 candidate target files for investigation or exit early with `NO_RELEVANT_FILES`.

### Sandbox & Reproduction

- [ ] **SANDBOX-01**: Initialize an isolated execution sandbox populated with target repository code and dependencies.
- [ ] **SANDBOX-02**: Execute reproduction commands and capture compact failure summaries (test name, assertion, file:line).
- [ ] **SANDBOX-03**: Detect false-positive passes and abort with `NOT_REPRODUCED` before generating unnecessary patches.
- [ ] **SANDBOX-04**: Create immutable filesystem checkpoints following successful failure reproduction.

### Speculative Branching

- [ ] **BRANCH-01**: Fork checkpointed sandbox state into K candidate sandboxes in parallel (`asyncio.gather`).
- [ ] **BRANCH-02**: Generate K candidate patches using distinct prompt strategies (e.g. minimal, root-cause, defensive).
- [ ] **BRANCH-03**: Apply unified diff patches to candidate sandboxes and validate syntax and syntax integrity.

### Verification & Scoring

- [ ] **VERIFY-01**: Execute verification test suites concurrently across all active candidate branches.
- [ ] **VERIFY-02**: Compute deterministic patch scores based on reproduction test passing, regression minimization, diff line brevity, and execution time.
- [ ] **VERIFY-03**: Immediately cancel running competitor branches via asyncio cancellation upon a clean candidate pass.
- [ ] **VERIFY-04**: Grade winning candidates against hidden benchmark tests in an isolated post-run evaluation environment.

### Delivery & GitHub Integration

- [ ] **DELIVER-01**: Package winning candidate diff, test reproduction evidence, and root-cause summary.
- [ ] **DELIVER-02**: Create pull requests on target GitHub repositories when `GITHUB_TOKEN` is provided and `OPEN_PR=true`.
- [ ] **DELIVER-03**: Emit terminal `run.finished` and `deliver.ready` events conforming to frozen JSON schemas.

### Live Observability & UI

- [ ] **UI-01**: Stream step progression, live terminal chunks, branch trees, and cost meters in real-time over SSE.
- [ ] **UI-02**: Render interactive @xyflow/react branch graphs with staggered springs, state color badges, and winner glowing transitions.
- [ ] **UI-03**: Provide dual Replay (deterministic canned playback) and Live (EventSource connection) streaming modes.
- [ ] **UI-04**: Render home showcase explorer and evaluation dashboard with Recharts comparison metrics and synthetic data warnings.

## v2 Requirements

### Extended Capabilities

- **EXT-01**: Multi-repo and monorepo cross-package dependency bug remediation.
- **EXT-02**: Interactive human-in-the-loop steering to select branch strategies before test execution.
- **EXT-03**: Automatic regression test synthesis committed alongside winning bugfix patches.

## Out of Scope

| Feature | Reason |
|---------|--------|
| Live paid API calls during development | All testing and development must use fake providers and cassette replays |
| Modifying frozen contract schemas | Contract stability guarantees cross-lane independence |
| Model-based patch ranking | LLM judges introduce evaluation drift; scoring must be deterministic code |
| Live hidden test access in agent sandboxes | Prevents benchmark data leakage and test overfitting |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SANDBOX-01 | Phase 1: Backend Foundation | Pending |
| SANDBOX-04 | Phase 1: Backend Foundation | Pending |
| UI-01 | Phase 2: Frontend Run View | Pending |
| UI-02 | Phase 2: Frontend Run View | Pending |
| UI-03 | Phase 2: Frontend Run View | Pending |
| UI-04 | Phase 3: Frontend Pages | Pending |
| TRIAGE-01 | Phase 4: Backend Agent Pipeline | Pending |
| TRIAGE-02 | Phase 4: Backend Agent Pipeline | Pending |
| TRIAGE-03 | Phase 4: Backend Agent Pipeline | Pending |
| SANDBOX-02 | Phase 4: Backend Agent Pipeline | Pending |
| SANDBOX-03 | Phase 4: Backend Agent Pipeline | Pending |
| BRANCH-01 | Phase 4: Backend Agent Pipeline | Pending |
| BRANCH-02 | Phase 4: Backend Agent Pipeline | Pending |
| BRANCH-03 | Phase 4: Backend Agent Pipeline | Pending |
| VERIFY-01 | Phase 4: Backend Agent Pipeline | Pending |
| VERIFY-02 | Phase 4: Backend Agent Pipeline | Pending |
| VERIFY-03 | Phase 4: Backend Agent Pipeline | Pending |
| VERIFY-04 | Phase 4: Backend Agent Pipeline | Pending |
| DELIVER-01 | Phase 4: Backend Agent Pipeline | Pending |
| DELIVER-02 | Phase 4: Backend Agent Pipeline | Pending |
| DELIVER-03 | Phase 4: Backend Agent Pipeline | Pending |

# Architecture & Operating Decisions

## DEC-001: Technology Stack Selection
- source: AGENTS.md
- status: locked
- decision: Backend must use Python 3.12, FastAPI, httpx, pydantic, and SQLite with import root `backend/` (`app.*`). Frontend must use Next.js 15 App Router, React 19, TypeScript, Tailwind v4, shadcn/ui, motion/react, @xyflow/react, lucide-react, cmdk, and recharts.
- scope: backend stack, frontend stack

## DEC-002: Frozen Contracts Authority
- source: AGENTS.md
- status: locked
- decision: The contracts in `contracts/events.schema.json`, `contracts/openapi.yaml`, and `contracts/interfaces.md` are frozen. Agents must never edit `contracts/` directly; change requests must be appended to `contracts/CHANGE_REQUESTS.md`.
- scope: contracts, interfaces, api schema, event schema

## DEC-003: Design Tokens Only for Styling
- source: AGENTS.md
- status: locked
- decision: All frontend styling must consume tokens from `frontend/styles/tokens.css`. Never hard-code colour hex/rgb values.
- scope: frontend styling, design tokens

## DEC-004: Strict Environment Variable Security
- source: AGENTS.md
- status: locked
- decision: Never read, print, log, or commit `.env`. All configuration must come from environment variables. Agents must never ask users for API keys.
- scope: security, environment variables, credentials

## DEC-005: Zero Live API Calls in Development/Agent Sessions
- source: AGENTS.md
- status: locked
- decision: Agents must never make live calls to paid or rate-limited APIs (Nebius, NVIDIA, Tavily, GitHub, Contree). All automated development and testing must use fake providers or cassette replay. Only the project owner runs `backend/tools/smoke.py` with real keys.
- scope: api access, fake providers, cost control, smoke tests

## DEC-006: Non-Destructive Shell Operations
- source: AGENTS.md
- status: locked
- decision: Operations must stay inside the repository. No destructive shell commands, no force pushes, and agents must never merge into `master` directly.
- scope: git safety, shell execution

## DEC-007: Exact Dependency Pinning
- source: AGENTS.md
- status: locked
- decision: Pin every dependency exactly in requirements and package files. Keep dependencies minimal and add one only when required by the task.
- scope: dependencies, python packages, npm packages

## DEC-008: External API Abstraction Boundary
- source: AGENTS.md
- status: locked
- decision: Do not invent external APIs. Unknown external APIs must sit behind interface abstractions and be marked `TODO(VERIFY)`.
- scope: external integrations, interface contracts

## DEC-009: File Size and Repository Scan Constraints
- source: AGENTS.md
- status: locked
- decision: Keep every file under approximately 300 lines. Agents must not scan the entire repository blindly; read only targeted files required for the task.
- scope: code quality, agent execution efficiency

## DEC-010: Failure Recovery Protocol
- source: AGENTS.md
- status: locked
- decision: If an item fails twice, stop the item immediately, record the exact error in `NOTES.md`, and move on.
- scope: error handling, failure protocol

## DEC-011: Multi-Agent Lane Isolation and Ownership
- source: AGENTS.md
- status: locked
- decision: Development is split across isolated lane branches (one agent per lane): Backend Foundation (`lane/backend-foundation`), Backend Agent (`lane/backend-agent`), Smoke (`lane/smoke`), UI Run View (`lane/ui-run`), and UI Pages (`lane/ui-pages`). Backend Agent begins only after Backend Foundation is merged. Shared frontend files belong to the project owner.
- scope: multi-agent coordination, branch lanes, file ownership

## DEC-012: Speculative Parallel Branching with Deterministic Scoring
- source: AGENTS.md
- status: locked
- decision: Branching must evaluate K candidates with different strategy prompts in parallel (`asyncio.gather`). Scoring, ranking, diff size calculation, and pass counts must be deterministic code, never model calls.
- scope: speculative branching, candidate ranking, patch scoring

## DEC-013: Hard Cost Guards and Event Tier Aliases
- source: AGENTS.md
- status: locked
- decision: Enforce hard budget limits in SQLite (`HARD_CAP_USD` for Nebius, `CALL_CAP` for NVIDIA, `RUN_BUDGET_USD` default 0.08, `LIVE_ENABLED` default false). Event `model_tier` must strictly be `lightning|super|ultra|none` and never a raw model name.
- scope: budget guards, cost control, event logging

## DEC-014: Hidden Test Isolation
- source: AGENTS.md
- status: locked
- decision: Hidden benchmark tests are used exclusively to grade candidate patches at verification time in a fresh sandbox copy; they must never be exposed to the agent or copied into the agent's work sandbox.
- scope: evaluation, benchmark grading, anti-leakage

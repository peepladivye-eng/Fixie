# Fixie: Agent Guidelines

Fixie takes a GitHub issue (or fixture/benchmark instance), reproduces the bug in a sandbox, forks the sandbox
state into several candidate patches, runs tests on all of them in parallel, scores them with deterministic code,
keeps the winner, and delivers a diff, test evidence and a PR. A web UI streams the run as a step timeline, a
terminal and a branch tree. Built for the Nebius x NVIDIA Global AI Hackathon, Track 1.

This file is the single source of truth. Tool-specific rule files (e.g. `.agent/rules/`) must only point here.

## 1. Stack
- Backend: Python 3.12, FastAPI, httpx, pydantic, SQLite. Import root is `backend/` (modules are `app.*`;
  run commands from `backend/` or rely on `pythonpath` in `pytest.ini`).
- Frontend: Next.js 15 App Router, React 19, TypeScript, Tailwind v4, shadcn/ui, `motion/react`, `@xyflow/react`,
  `lucide-react`, `cmdk`, `recharts`.
- Contracts (FROZEN): `contracts/events.schema.json`, `contracts/openapi.yaml`, `contracts/interfaces.md`.
- Design tokens: `frontend/styles/tokens.css` only. Never hard-code a colour.

## 2. Hard rules
1. Never read, print, log or commit `.env`. Config comes from environment variables. Never ask for keys.
2. Agents never make live calls to paid or rate-limited APIs (Nebius, NVIDIA, Tavily, GitHub, Contree). Everything
   is built and tested on FAKE providers. Only the project owner runs `backend/tools/smoke.py` with real keys.
3. No destructive shell commands. Work only inside this repo. No force pushes. Never merge into `master` yourself.
4. Pin every dependency exactly. Keep dependencies few; add one only when the task needs it.
5. Do not invent APIs. Unknown external APIs go behind an interface and are marked `TODO(VERIFY)`.
6. Never edit `contracts/`. If you need a change, append a request to `contracts/CHANGE_REQUESTS.md` and stop.
7. Keep every file under about 300 lines. Do not scan the whole repo; read only the files you need.
8. No plan documents, walkthroughs or extra artifacts. No screenshots or browser-tool runs except in a prompt's
   final acceptance step. No long-running servers in agent sessions; tests use in-process clients.
9. If something fails twice, stop that item, record the exact error in `NOTES.md`, and move on.
10. Commit after every stage on your own branch with a clear message.

## 3. Lanes and ownership (one agent per lane, one branch per lane)
| Lane | Branch | Owns |
|---|---|---|
| Backend A: foundation | `lane/backend-foundation` | `backend/app/llm.py`, `models.json`, `sandbox.py`, `main.py`, `replay.py`, `limits.py`, `store.py`, `backend/tests/`, `scripts/` |
| Backend B: agent | `lane/backend-agent` | `backend/app/agent/`, `search.py`, `github.py`, `backend/eval/` |
| Smoke | `lane/smoke` | `backend/tools/smoke.py` only |
| UI run view | `lane/ui-run` | `frontend/lib/`, `frontend/components/run/`, `frontend/app/run/` |
| UI pages | `lane/ui-pages` | `frontend/app/page.tsx`, `frontend/app/eval/`, `frontend/components/{home,eval,states}/` |

Backend B starts only after Backend A is merged. Shared frontend files (`layout.tsx`, `package.json`) belong to
the project owner; report needed changes in your final message instead of editing them (add new dependencies to
`package.json` only if your prompt says so).

## 4. Commands
```powershell
# one-time
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install -r backend/requirements.txt
# checks
.\.venv\Scripts\python scripts/check.py              # validator + pytest
.\.venv\Scripts\python scripts/check.py --frontend   # also frontend lint + build
# backend (from repo root)
cd backend; ..\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
# frontend
cd frontend; npm install; npm run dev -- -p 3000
```
`scripts/check.py` is the one verification command. Run it instead of improvising.

## 5. Product rules that must hold
- Branching means K candidates with DIFFERENT strategy prompts, evaluated in PARALLEL (`asyncio.gather`).
- Scoring, ranking, diff size and pass counts are deterministic code, never model calls.
- The patch model must see relevant code and a compact failing-test summary, never only the issue text.
- `model_tier` in events is `lightning|super|ultra|none`, never a model name.
- Cost guards are real: `HARD_CAP_USD` (Nebius), `CALL_CAP` (NVIDIA), `RUN_BUDGET_USD` (default 0.08),
  `LIVE_ENABLED` default false. Cassette mode and the response cache make repeat runs free.
- Synthetic numbers must be flagged `synthetic: true` and never presented as results.
- Hidden tests are used only to grade, never exposed to the agent or copied into its sandbox.

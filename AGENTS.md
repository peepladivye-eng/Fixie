# Fixie: Agent Guidelines & Multi-Prompt Protocol

Fixie is an autonomous bug reproduction and speculative patch engine built for the **Nebius x NVIDIA Global AI Hackathon (Track 1: Coding and Agentic Engineering)**.
Fixie ingests a GitHub issue, reproduces the bug in an isolated sandbox, forks the sandbox state into several candidate patches simultaneously, tests them concurrently, evaluates test evidence, and delivers the winning patch with diff, reproduction proof, and pull request.

---

## 1. Project Summary & Architecture Stack

- **Backend**: Python 3.12, FastAPI, Pydantic, SQLite (runs/replays), Contree-SDK / Sandbox abstraction, Nebius Token Factory / NVIDIA NIM LLM client abstraction.
- **Frontend**: Next.js 15 (App Router), React 19, TypeScript, Tailwind CSS v4, shadcn/ui, motion (Framer Motion), `@xyflow/react`, `lucide-react`, `cmdk`.
- **Contracts**: Frozen schemas and interfaces in `contracts/` defining SSE event streams and REST endpoints.
- **Visual Palette**: Strict design tokens in `frontend/styles/tokens.css` (Background `#0B0D10`, Surface `#12151A`, Border `#1F242C`, Text `#E8EAED`, Text-Muted `#9AA3AE`, Accent Amber `#F5A524`, Pass `#3DD68C`, Fail `#F0616D`, Badge-Blue `#6EA8FE`).

---

## 2. Hard Rules (Non-Negotiable)

1. **Zero cost**: Never call any paid API and never add payment information. All development uses fake/mock implementations. No live API keys exist during Day 0 development.
2. **Secrets & Environment Variables**:
   - Never read, print, or commit `.env`.
   - Do NOT create a `.env` file containing secrets.
   - Only `.env.example` is committed with empty keys (`NEBIUS_API_KEY`, `NEBIUS_PROJECT_ID`, `NVIDIA_API_KEY`, `TAVILY_API_KEY`, `GITHUB_TOKEN`).
   - Read configurations exclusively from environment variables with safe defaults.
   - Never prompt the user for API keys.
3. **No destructive commands**:
   - No `rm -rf` outside this repository.
   - No force pushes (`git push --force`).
   - Work strictly inside this repository workspace.
   - Commit with clear, descriptive messages.
4. **Pinned dependencies**:
   - Pin all dependency versions strictly in `requirements.txt` and `package.json`.
   - Keep dependencies minimal.
5. **No invented APIs**:
   - Where external API structures (Nebius, NVIDIA, Contree SDK, etc.) are unverified, place them behind an interface and tag them with `TODO(VERIFY)`.

---

## 3. Folder Ownership & Parallel Lanes

To prevent merge collisions across parallel agent prompts, files and directories are partitioned into strict ownership lanes:

| Lane / Prompt | Owned Scope | Responsibilities |
|---|---|---|
| **Prompt 1 (Backend)** | `backend/` | FastAPI server, SSE streaming, agent loop, step runners, mock sandboxes, event validator |
| **Prompt 2 (Run Studio UI)** | `frontend/lib/`, `frontend/components/run/`, `frontend/app/run/` | Live SSE hooks, Timeline component, Terminal Chunk viewer, Branch Tree (`@xyflow/react`), Winner Diff view |
| **Prompt 3 (Frontend Shell)** | `frontend/app/` (except `/run`), `frontend/components/` (except `/run`), `frontend/styles/` | App shell, navigation, Showcase gallery, benchmark eval dashboard, modal dialogs, empty states |
| **Global Contracts (FROZEN)** | `contracts/` | Schema and interface definition. **No lane may modify directly!** |

### Contract Change Protocol
- **Lanes MUST NEVER directly edit files under `contracts/`.**
- If a schema or interface modification is needed, the lane must append an entry to `contracts/CHANGE_REQUESTS.md`.

---

## 4. Exact Commands to Run

### Backend
```bash
# Install dependencies
pip install -r backend/requirements.txt

# Run event schema validator on sample replay
python -m backend.tools.validate_events replays/sample_run.jsonl

# Run unit tests
pytest

# Start FastAPI development server
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend
```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Run Next.js production build
npm run build

# Start Next.js development server
npm run dev -- -p 3000
```

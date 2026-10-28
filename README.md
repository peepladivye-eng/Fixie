# Fixie 🔧

> **Autonomous Bug Reproduction and Speculative Patch Engine**  
> *Nebius x NVIDIA Global AI Hackathon (Track 1: Coding and Agentic Engineering)*

Fixie automates software bug remediation from issue report to tested pull request:
1. **Triage & Ingestion**: Ingests GitHub issues or benchmark tasks.
2. **Reproduction Sandbox**: Spins up a container sandbox, reproduces the issue, and captures test failure evidence.
3. **Speculative Branching**: Checkpoints the sandbox state and forks it into multiple candidate patch strategies concurrently.
4. **Parallel Verification**: Executes full test suites on all branches in parallel.
5. **Winner Selection & Delivery**: Scores candidate patches, picks the verified winner, and delivers unified diffs, execution logs, and pull requests.
6. **Live Observability**: Streams the entire lifecycle in real time via Server-Sent Events (SSE) into a dark-mode dashboard featuring a step timeline, live terminal chunk streaming, and interactive branch trees.

---

## Architecture & Monorepo Layout

```
Fixie/
├── contracts/               # Frozen schema & API contracts
│   ├── events.schema.json   # JSON Schema for all streaming events
│   ├── openapi.yaml         # REST & SSE OpenAPI specification
│   ├── interfaces.md        # Language-neutral interface signatures
│   └── CHANGE_REQUESTS.md   # Change log for contract revisions
├── backend/                 # Python 3.12 / FastAPI service
│   ├── app/                 # Core backend application
│   │   ├── main.py          # FastAPI application & SSE streaming endpoints
│   │   ├── agent/           # Orchestrator & step runners
│   │   ├── llm.py           # Token Factory / NVIDIA NIM client abstraction
│   │   ├── sandbox.py       # Contree-SDK / Sandbox fork & execution abstraction
│   │   ├── search.py        # Web & doc search abstraction (Tavily)
│   │   ├── github.py        # GitHub issue ingestion & PR creation
│   │   └── store.py         # SQLite run persistence & event replay
│   ├── eval/                # Benchmark evaluation harness
│   ├── tools/               # Validation & utility scripts
│   └── tests/               # Backend unit and integration tests
├── frontend/                # Next.js 15 (App Router, Tailwind v4, shadcn/ui)
├── replays/                 # Pre-recorded event streams and showcase runs
│   ├── sample_run.jsonl     # Sample duration-parser reproduction & patch run
│   └── showcase.json        # Showcase run catalog
├── AGENTS.md                # Multi-prompt agent protocol & lane ownership
├── LICENSE                  # MIT License
└── .env.example             # Template environment variables
```

---

## Quickstart

### 1. Prerequisites
- Python 3.12+
- Node.js 20+ & npm

### 2. Backend Setup
```bash
# Install Python dependencies
pip install -r backend/requirements.txt

# Validate the sample run replay against JSON schema
python -m backend.tools.validate_events replays/sample_run.jsonl

# Run pytest suite
pytest

# Launch backend API server
uvicorn backend.app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to view the Fixie studio dashboard.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

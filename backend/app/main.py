"""Fixie FastAPI application entry point.

Implements REST and SSE streaming endpoints as specified in contracts/openapi.yaml.
"""

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

app = FastAPI(
    title="Fixie API",
    version="1.0.0",
    description="Autonomous Bug Reproduction and Speculative Patch Engine API",
)

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateRunRequest(BaseModel):
    source: str = Field(..., description="GitHub issue URL or instance ID")
    mode: str = Field("replay", description="Execution mode: live or replay")


class CreateRunResponse(BaseModel):
    run_id: str


class HealthResponse(BaseModel):
    status: str
    live_enabled: bool
    daily_runs_left: int


@app.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Service health and runtime configuration flags."""
    return HealthResponse(
        status="ok",
        live_enabled=False,  # Zero-cost Day 0 default: fake/replay only
        daily_runs_left=25,
    )


@app.post("/runs", response_model=CreateRunResponse, status_code=status.HTTP_201_CREATED)
def create_run(req: CreateRunRequest) -> CreateRunResponse:
    """Create a new triage and patch run."""
    # TODO(VERIFY): Connect to agent loop execution in Prompt 1 backend lane
    return CreateRunResponse(run_id="run_20261028_parse_duration")


@app.get("/runs/{id}")
def get_run(id: str) -> Dict[str, Any]:
    """Get metadata and current status for a specific run."""
    # TODO(VERIFY): Connect to store.py in Prompt 1 backend lane
    return {
        "id": id,
        "source": "https://github.com/fast-utils/duration-parser/issues/14",
        "mode": "replay",
        "status": "success",
        "issue_title": "parse_duration('1h30m') yields 90 instead of 5400",
        "repo": "fast-utils/duration-parser",
        "total_cost_usd": 0.0894,
        "total_seconds": 89.2,
        "created_at": "2026-10-28T14:00:00Z",
    }


@app.get("/runs/{id}/events")
def stream_run_events(id: str, last_event_id: Optional[str] = Header(None, alias="Last-Event-ID")):
    """Server-Sent Events endpoint streaming run lifecycle events."""
    # TODO(VERIFY): Implement SSE event generator reading from store/replays
    def event_generator():
        yield f": ping\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/showcase")
def list_showcase() -> List[Dict[str, Any]]:
    """Return showcase runs catalog."""
    # TODO(VERIFY): Connect to store.py / replays/showcase.json
    return [
        {
            "id": "run_20261028_parse_duration",
            "title": "parse_duration('1h30m') yields 90 instead of 5400",
            "repo": "fast-utils/duration-parser",
            "summary": "Fixed unit multiplier dictionary mapping 'h' to 60 instead of 3600 seconds with 3 parallel speculative branches.",
        }
    ]


@app.get("/eval/summary")
def get_eval_summary() -> Dict[str, Any]:
    """Return evaluation metrics summary."""
    return {
        "total_instances": 30,
        "resolved_instances": 24,
        "resolution_rate": 0.80,
        "avg_cost_usd": 0.089,
        "avg_duration_seconds": 88.5,
    }

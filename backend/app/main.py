"""FastAPI application entry point with SSE streaming and contract-compliant endpoints."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from .emitter import EventEmitter
from .limits import LiveRunLimiter, LiveRunSlots
from .replay import run_replay, resolve_replay_path
from .store import RunStore

if os.getenv("FIXIE_FORCE_FAKE_RUNNER") == "1":
    from .fake_runner import run_agent
else:
    try:
        from app.agent.runner import run_agent  # type: ignore[import-not-found]
    except ImportError:
        from .fake_runner import run_agent

BASE_DIR = Path(__file__).resolve().parents[1]
_db_path = os.getenv("FIXIE_DB", str(BASE_DIR / "fixie.db"))
store = RunStore(_db_path)
limiter = LiveRunLimiter(_db_path)
slots = LiveRunSlots()
emitters: dict[str, EventEmitter] = {}
logger = logging.getLogger("fixie.api")

SOURCE_PATTERN = re.compile(
    r"^(fixture:[a-z0-9_-]+|instance:[A-Za-z0-9_-]+|https://github\.com/[^/\s]+/[^/\s]+/issues/[1-9][0-9]*|[A-Za-z0-9_.-]+)$"
)


class RunRequest(BaseModel):
    source: str = Field(min_length=1, max_length=4096)
    mode: Literal["live", "replay"]
    speed: float = Field(default=1.0, gt=0, le=1000)


def _live_enabled() -> bool:
    # Default is false per spec: LIVE_ENABLED env default false
    val = os.getenv("LIVE_ENABLED", os.getenv("FIXIE_LIVE_ENABLED", "false")).lower()
    return val in {"1", "true", "yes"}


async def request_log(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(json.dumps({"request_id": request_id, "method": request.method, "path": request.url.path, "status": response.status_code}))
    return response


@asynccontextmanager
async def lifespan(_: FastAPI):
    await store.initialize()
    yield


app = FastAPI(title="Fixie API", lifespan=lifespan)
app.middleware("http")(request_log)
origins = [origin.strip() for origin in os.getenv("FIXIE_CORS_ORIGINS", "*").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins or ["*"], allow_credentials=False, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    code = "ERROR"
    message = str(exc.detail)
    if isinstance(exc.detail, dict):
        code = exc.detail.get("error", exc.detail.get("code", "ERROR"))
        message = exc.detail.get("message", str(exc.detail))
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": code, "message": message},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"error": "INVALID_REQUEST", "message": str(exc)},
    )


async def _execute(run_id: str, request: RunRequest, emitter: EventEmitter) -> None:
    try:
        if request.mode == "live":
            await run_agent(request.source, emitter.emit, {"k_branches": 3, "max_rounds": 2})
        else:
            await run_replay(request.source, emitter.emit, request.speed)
    except Exception as exc:
        await emitter.emit("run.error", {"code": "RUNNER_FAILED", "message": str(exc)})
        await emitter.emit("run.finished", {"status": "failed", "total_cost_usd": 0.0, "total_seconds": 0.0})
    finally:
        if request.mode == "live":
            await slots.release()
        emitters.pop(run_id, None)


@app.post("/runs", status_code=status.HTTP_201_CREATED)
async def create_run(payload: RunRequest, request: Request) -> dict[str, str]:
    if not SOURCE_PATTERN.fullmatch(payload.source):
        raise HTTPException(
            status_code=422,
            detail={"error": "INVALID_SOURCE", "message": "source must be fixture:<name>, instance:<id>, or a GitHub issue URL."},
        )

    if payload.mode == "live":
        if not _live_enabled():
            raise HTTPException(
                status_code=429,
                detail={"error": "LIVE_PAUSED", "message": "Live execution is currently disabled."},
            )
        if payload.source.startswith("fixture:") and os.getenv("FIXIE_ALLOW_LOCAL") != "1":
            raise HTTPException(
                status_code=403,
                detail={"error": "LOCAL_DISABLED", "message": "Fixture sources require FIXIE_ALLOW_LOCAL=1."},
            )
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() if os.getenv("TRUST_PROXY") == "1" else (request.client.host if request.client else "unknown")
        if not await limiter.reserve(client_ip):
            raise HTTPException(
                status_code=429,
                detail={"error": "LIVE_PAUSED", "message": "Live-run capacity is paused for today."},
            )
        if not await slots.acquire():
            raise HTTPException(
                status_code=429,
                detail={"error": "LIVE_BUSY", "message": "Live-run concurrency capacity is full."},
            )
    else:
        # Replay mode: verify replay exists without silent fallback
        try:
            resolve_replay_path(payload.source)
        except FileNotFoundError as exc:
            raise HTTPException(
                status_code=404,
                detail={"error": "NOT_FOUND", "message": str(exc)},
            )

    run_id = str(uuid.uuid4())
    await store.create_run({
        "run_id": run_id,
        "source": payload.source,
        "mode": payload.mode,
        "status": "running",
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    emitter = EventEmitter(store, run_id)
    await emitter.initialize()
    emitters[run_id] = emitter
    asyncio.create_task(_execute(run_id, payload, emitter))
    return {"run_id": run_id}


@app.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    run = await store.get_run(run_id, include_events=False)
    if run is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Run not found"})
    return {
        "id": run["run_id"],
        "source": run["source"],
        "mode": run["mode"],
        "status": run["status"],
        "issue_title": run.get("issue_title") or "",
        "repo": run.get("repo") or "",
        "total_cost_usd": float(run.get("total_cost_usd", 0.0)),
        "total_seconds": float(run.get("total_seconds", 0.0)),
        "created_at": run["created_at"],
    }


def _last_event(value: str | None) -> int:
    try:
        return int(value) if value is not None else -1
    except ValueError:
        return -1


@app.get("/runs/{run_id}/events")
async def events(run_id: str, last_event_id: str | None = Header(default=None, alias="Last-Event-ID")) -> StreamingResponse:
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"error": "NOT_FOUND", "message": "Run not found"})

    last_seq = _last_event(last_event_id)

    # Check if run is already finished and client is asking for events beyond the end
    prior_events = await store.events_after(run_id, -1)
    if run["status"] in ("success", "failed"):
        max_seq = prior_events[-1]["seq"] if prior_events else -1
        if last_seq >= max_seq:
            # Reconnected past end of finished run: return empty stream cleanly
            async def empty_stream():
                if False:
                    yield ""
            return StreamingResponse(empty_stream(), media_type="text/event-stream")

    emitter = emitters.get(run_id)
    if emitter is None:
        emitter = EventEmitter(store, run_id)
        await emitter.initialize()
        if run["status"] == "running":
            emitters[run_id] = emitter

    async def stream():
        subscription = emitter.subscribe(last_seq)
        while True:
            try:
                event = await asyncio.wait_for(anext(subscription), timeout=15)
            except TimeoutError:
                yield ": heartbeat\n\n"
                continue
            except StopAsyncIteration:
                break
            yield f"id: {event['seq']}\nevent: {event['type']}\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"
            # Close only after run.finished (not run.error so client gets the final finished event)
            if event["type"] == "run.finished":
                await subscription.aclose()
                emitters.pop(run_id, None)
                return

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/showcase")
async def showcase() -> list[dict]:
    return await store.showcase()


@app.get("/eval/summary")
async def eval_summary() -> dict:
    path = BASE_DIR / "eval" / "eval.json"
    if not path.is_file():
        raise HTTPException(
            status_code=404,
            detail={"error": "NOT_FOUND", "message": "Evaluation summary is not available yet. Run backend/eval/run_eval.py first."},
        )
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "live_enabled": _live_enabled(),
        "daily_runs_left": await limiter.daily_runs_left(),
        "runs_in_progress": slots.active,
        "version": os.getenv("FIXIE_VERSION", "dev"),
    }

from __future__ import annotations

import asyncio
import json
import os
import uuid
import logging
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .emitter import EventEmitter
from .limits import LiveRunLimiter, LiveRunSlots
from .replay import run_replay
from .store import RunStore

if os.getenv("FIXIE_FORCE_FAKE_RUNNER") == "1":
    from .fake_runner import run_agent
else:
    try:
        from app.agent.runner import run_agent  # type: ignore[import-not-found]
    except ImportError:
        from .fake_runner import run_agent

BASE_DIR = Path(__file__).resolve().parents[1]
store = RunStore(os.getenv("FIXIE_DB", str(BASE_DIR / "fixie.db")))
limiter = LiveRunLimiter()
slots = LiveRunSlots()
emitters: dict[str, EventEmitter] = {}
logger = logging.getLogger("fixie.api")
SOURCE_PATTERN = re.compile(r"^(fixture:[a-z0-9_-]+|instance:[A-Za-z0-9_-]+|https://github\.com/[^/\s]+/[^/\s]+/issues/[1-9][0-9]*)$")


class RunRequest(BaseModel):
    source: str = Field(min_length=1, max_length=4096)
    mode: Literal["live", "replay"]
    speed: float = Field(default=1.0, gt=0, le=1000)


def _live_enabled() -> bool:
    return os.getenv("FIXIE_LIVE_ENABLED", "1").lower() not in {"0", "false", "no"}


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


async def _execute(run_id: str, request: RunRequest, emitter: EventEmitter) -> None:
    try:
        if request.mode == "live":
            await run_agent(request.source, emitter.emit, {"k_branches": 3, "max_rounds": 2})
        else:
            await run_replay(request.source, emitter.emit, request.speed)
    except Exception as exc:  # runner failures must remain visible to clients
        await emitter.emit("run.error", {"code": "RUNNER_FAILED", "message": str(exc)})
        await emitter.emit("run.finished", {"status": "failed", "total_cost_usd": 0.0, "total_seconds": 0.0})
    finally:
        if request.mode == "live":
            await slots.release()


@app.post("/runs")
async def create_run(payload: RunRequest, request: Request) -> dict[str, str]:
    if not SOURCE_PATTERN.fullmatch(payload.source):
        raise HTTPException(status_code=422, detail={"code": "INVALID_SOURCE", "message": "source must be fixture:<name>, instance:<id>, or a GitHub issue URL."})
    if payload.mode == "live":
        if payload.source.startswith("fixture:") and os.getenv("FIXIE_ALLOW_LOCAL") != "1":
            raise HTTPException(status_code=403, detail={"code": "LOCAL_DISABLED", "message": "Fixture sources require FIXIE_ALLOW_LOCAL=1."})
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip() if os.getenv("TRUST_PROXY") == "1" else (request.client.host if request.client else "unknown")
        if not _live_enabled() or not await limiter.reserve(client_ip):
            raise HTTPException(status_code=429, detail={"code": "LIVE_PAUSED", "message": "Live-run capacity is paused for today."})
        if not await slots.acquire():
            raise HTTPException(status_code=429, detail={"code": "LIVE_BUSY", "message": "Live-run concurrency capacity is full."})
    run_id = str(uuid.uuid4())
    await store.create_run({"run_id": run_id, "source": payload.source, "mode": payload.mode, "status": "running", "created_at": datetime.now(timezone.utc).isoformat()})
    emitter = EventEmitter(store, run_id)
    await emitter.initialize()
    emitters[run_id] = emitter
    asyncio.create_task(_execute(run_id, payload, emitter))
    return {"run_id": run_id}


@app.get("/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    run = await store.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    for event in run["events"]:
        event.pop("data_json", None)
    return run


def _last_event(value: str | None) -> int:
    try:
        return int(value) if value is not None else -1
    except ValueError:
        return -1


@app.get("/runs/{run_id}/events")
async def events(run_id: str, last_event_id: str | None = Header(default=None, alias="Last-Event-ID")) -> StreamingResponse:
    if await store.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    emitter = emitters.get(run_id)
    if emitter is None:
        emitter = EventEmitter(store, run_id)
        await emitter.initialize()
        emitters[run_id] = emitter

    async def stream():
        subscription = emitter.subscribe(_last_event(last_event_id))
        while True:
            try:
                event = await asyncio.wait_for(anext(subscription), timeout=15)
            except TimeoutError:
                yield ": heartbeat\n\n"
                continue
            yield f"id: {event['seq']}\nevent: {event['type']}\ndata: {json.dumps(event, separators=(',', ':'))}\n\n"
            if event["type"] in {"run.finished", "run.error"}:
                await subscription.aclose()
                return

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/showcase")
async def showcase() -> list[dict]:
    return await store.showcase()


@app.get("/eval/summary")
async def eval_summary() -> dict:
    path = BASE_DIR / "eval" / "eval.json"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Evaluation summary is not available yet. Run backend/eval/run_eval.py first.")
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "live_enabled": _live_enabled(), "daily_runs_left": await limiter.daily_runs_left(), "runs_in_progress": slots.active, "version": os.getenv("FIXIE_VERSION", "dev")}

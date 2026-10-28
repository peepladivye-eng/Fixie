"""Record a fake/local run as a replay without replacing existing recordings."""
import argparse, asyncio, json, sys, uuid
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.fake_runner import run_agent

ROOT = Path(__file__).parent
REPLAYS = ROOT.parent / "replays"

async def record(source: str) -> Path:
    events = []
    async def emit(kind, data):
        events.append({"run_id":"recording", "seq":len(events), "ts":datetime.now(timezone.utc).isoformat(), "type":kind, "data":data})
    await run_agent(source, emit, {"k_branches":3, "max_rounds":2})
    if not events or [e["seq"] for e in events] != list(range(len(events))): raise ValueError("invalid event stream")
    REPLAYS.mkdir(exist_ok=True); recording_id = uuid.uuid4().hex; output = REPLAYS / f"{recording_id}.jsonl"
    output.write_text("".join(json.dumps(e) + "\n" for e in events), encoding="utf-8")
    showcase = REPLAYS / "showcase.json"; entries = json.loads(showcase.read_text()) if showcase.exists() else []
    entries.append({"id":recording_id, "title":events[0]["data"].get("issue_title","Recording"), "repo":events[0]["data"].get("repo","unknown"), "summary":"Recorded zero-cost fake run"})
    showcase.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("source")
    print(asyncio.run(record(parser.parse_args().source)))

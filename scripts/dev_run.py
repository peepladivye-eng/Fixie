"""Owner-run script: run a fixture through run_agent_loop and record the event stream.

Usage:
    python scripts/dev_run.py [fixture_name] [--allow-paid]

Output:
    - One-line-per-event timeline printed to stdout.
    - Events written to replays/dev_<provider>_<fixture>.jsonl.
    - Total cost and provider printed at the end.

Safety:
    Refuses to run with a paid provider (nebius, nvidia) unless --allow-paid is passed.
    Never prints API keys.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

SAFE_PROVIDERS = {"fake", "cassette", "gemini"}


def make_run_id(provider: str, fixture: str) -> str:
    return f"dev_{provider}_{fixture}_{int(time.time())}"


async def main() -> None:
    parser = argparse.ArgumentParser(description="Fixie dev runner (owner use only)")
    parser.add_argument("fixture", nargs="?", default="parse_duration", help="Fixture name (default: parse_duration)")
    parser.add_argument("--allow-paid", action="store_true", help="Allow paid providers (nebius, nvidia)")
    args = parser.parse_args()

    provider = os.getenv("LLM_PROVIDER", "fake").lower()
    fixture = args.fixture

    if provider not in SAFE_PROVIDERS and not args.allow_paid:
        print(
            f"ERROR: LLM_PROVIDER={provider!r} is a paid provider.\n"
            f"Use --allow-paid to proceed, or set LLM_PROVIDER to one of: {', '.join(sorted(SAFE_PROVIDERS))}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Required to allow LocalSandbox to run
    os.environ["FIXIE_ALLOW_LOCAL"] = "1"
    venv_scripts = str(Path(sys.executable).parent)
    os.environ["PATH"] = f"{venv_scripts}{os.pathsep}{os.environ.get('PATH', '')}"

    from app.agent.loop import run_agent_loop  # noqa: PLC0415 — deferred after path setup

    run_id = make_run_id(provider, fixture)
    source = f"fixture:{fixture}"
    events: list[dict] = []
    seq = 0

    async def emit(event_type: str, data: dict) -> None:
        nonlocal seq
        seq += 1
        ts = time.time()
        envelope = {
            "run_id": run_id,
            "seq": seq,
            "ts": ts,
            "type": event_type,
            "data": data,
        }
        events.append(envelope)
        print(f"{seq:03d}  {event_type}")

    print(f"provider={provider}  fixture={fixture}  run_id={run_id}")
    print("-" * 60)

    t_start = time.perf_counter()
    try:
        await run_agent_loop(source, emit, {"run_id": run_id})
    except Exception as exc:  # pragma: no cover
        print(f"FATAL: {exc}", file=sys.stderr)
        sys.exit(1)
    elapsed = time.perf_counter() - t_start

    # Compute total cost from llm.usage events
    total_cost = sum(
        float(e["data"].get("cost_usd", 0.0))
        for e in events
        if e["type"] == "llm.usage"
    )

    print("-" * 60)
    print(f"total_cost_usd={total_cost:.6f}  elapsed_s={elapsed:.2f}  provider={provider}")

    # Write replay
    replays_dir = ROOT / "replays"
    replays_dir.mkdir(exist_ok=True)
    out_path = replays_dir / f"dev_{provider}_{fixture}.jsonl"
    with out_path.open("w", encoding="utf-8") as fh:
        for envelope in events:
            fh.write(json.dumps(envelope) + "\n")
    print(f"replay written → {out_path}")


if __name__ == "__main__":
    asyncio.run(main())

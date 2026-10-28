"""Run baseline and branching evaluations, safely retaining completed instances."""
from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.agent.runner import run_agent

ROOT = Path(__file__).parent
OUTPUT = ROOT / "eval.json"


async def one_run(source: str, options: dict[str, Any]) -> dict[str, Any]:
    fixture_name = source.removeprefix("fixture:")
    events: list[dict[str, Any]] = []
    started = time.perf_counter()

    async def emit(event_type: str, data: dict[str, Any]) -> None:
        events.append({"type": event_type, "data": data})

    await run_agent(source, emit, options)

    deliver = next((e for e in reversed(events) if e["type"] == "deliver.ready"), None)
    winner_diff = deliver["data"].get("diff", "") if deliver else ""
    resolved = False
    if winner_diff:
        try:
            resolved = grade_with_hidden_tests(fixture_name, winner_diff)
        except Exception:
            resolved = False

    models: dict[str, dict[str, float]] = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
    for event in events:
        if event["type"] == "llm.usage":
            usage = event["data"]
            bucket = models[usage.get("model", "unknown")]
            bucket["input_tokens"] += int(usage.get("input_tokens", 0))
            bucket["output_tokens"] += int(usage.get("output_tokens", 0))
            bucket["cost_usd"] += float(usage.get("cost_usd", 0.0))

    rounds = sum(1 for e in events if e["type"] == "step.started" and e["data"].get("step") == "branch")
    return {
        "resolved": resolved,
        "rounds": max(1, rounds),
        "cost_usd": round(sum(v["cost_usd"] for v in models.values()), 6),
        "seconds": round(time.perf_counter() - started, 4),
        "per_model": dict(models),
    }


def aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
    model: dict[str, dict[str, float]] = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
    for item in items:
        for name, usage in item.get("per_model", {}).items():
            for key in ("input_tokens", "output_tokens", "cost_usd"):
                model[name][key] += usage.get(key, 0.0)

    total_cost = sum(x.get("cost_usd", 0.0) for x in items)
    total_seconds = sum(x.get("seconds", 0.0) for x in items)
    return {
        "resolved": sum(1 for x in items if x.get("resolved")),
        "rounds": sum(x.get("rounds", 0) for x in items),
        "cost_usd": round(total_cost, 6),
        "seconds": round(total_seconds, 4),
        "per_model": dict(model),
    }


def grade_with_hidden_tests(fixture_name: str, diff: str) -> bool:
    """Grade a candidate patch against hidden tests in an isolated fresh copy."""
    app_dir = Path(__file__).resolve().parents[1]
    candidates = [
        app_dir / "tests" / "core" / "fixtures" / fixture_name,
        app_dir / "eval" / "fixtures" / fixture_name,
    ]
    fixtures_dir = next((c for c in candidates if c.is_dir()), None)
    if fixtures_dir is None:
        raise FileNotFoundError(f"Fixture {fixture_name} not found")

    repo_src = fixtures_dir / "repo"
    hidden_src = fixtures_dir / "hidden_tests"

    with tempfile.TemporaryDirectory(prefix="fixie-grade-") as tmp:
        tmp_repo = Path(tmp) / "repo"
        shutil.copytree(repo_src, tmp_repo)

        # Apply candidate diff
        patch_file = Path(tmp) / "patch.diff"
        patch_file.write_text(diff, encoding="utf-8")
        apply_res = subprocess.run(
            ["git", "apply", "--no-index", "--ignore-space-change", "--whitespace=nowarn", str(patch_file)],
            cwd=str(tmp_repo),
            capture_output=True,
            text=True,
        )
        if apply_res.returncode != 0:
            return False

        # Copy hidden tests into repo tests directory
        if hidden_src.is_dir():
            target_dir = tmp_repo / "tests" if (tmp_repo / "tests").is_dir() else tmp_repo
            for item in hidden_src.glob("*.py"):
                shutil.copy2(item, target_dir / item.name)

        # Run pytest
        env = os.environ.copy()
        venv_scripts = str(Path(sys.executable).parent)
        env["PATH"] = f"{venv_scripts}{os.pathsep}{env.get('PATH', '')}"
        run_res = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=str(tmp_repo),
            capture_output=True,
            text=True,
            env=env,
        )
        return run_res.returncode == 0


async def main(fixtures: bool = False, repeat: int = 1) -> None:
    os.environ["FIXIE_ALLOW_LOCAL"] = "1"
    if fixtures:
        instances = [{"id": item.name, "source": f"fixture:{item.name}"} for item in sorted((ROOT / "fixtures").iterdir()) if item.is_dir()]
    else:
        instances = json.loads((ROOT / "instances.json").read_text(encoding="utf-8"))

    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"results": []}
    completed: dict[str, Any] = {item["id"]: item for item in previous.get("results", []) if "baseline" in item and "branching" in item}
    semaphore = asyncio.Semaphore(4)

    async def evaluate(instance: dict[str, str]) -> dict[str, Any]:
        inst_id = instance["id"]
        if inst_id in completed:
            return completed[inst_id]

        async with semaphore:
            errors = 0
            while errors < 2:
                try:
                    baseline_res = await one_run(instance["source"], {"baseline": True, "k_branches": 1, "max_rounds": 2})
                    branching_res = await one_run(instance["source"], {"baseline": False, "k_branches": 3, "max_rounds": 2})
                    res = {"id": inst_id, "baseline": baseline_res, "branching": branching_res}
                    completed[inst_id] = res
                    return res
                except Exception as exc:
                    errors += 1
                    if errors >= 2:
                        res = {
                            "id": inst_id,
                            "error": str(exc),
                            "baseline": {"resolved": False, "rounds": 0, "cost_usd": 0.0, "seconds": 0.0, "per_model": {}},
                            "branching": {"resolved": False, "rounds": 0, "cost_usd": 0.0, "seconds": 0.0, "per_model": {}},
                        }
                        completed[inst_id] = res
                        return res

    expanded = [{**item, "id": f"{item['id']}#{number}" if repeat > 1 else item["id"]} for item in instances for number in range(repeat)]
    results = await asyncio.gather(*(evaluate(item) for item in expanded))

    provider = os.getenv("LLM_PROVIDER", "fake").lower()
    synthetic = (provider == "fake")
    report = {
        "synthetic": synthetic,
        "provider": provider,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "instances_total": len(results),
        "baseline": aggregate([x["baseline"] for x in results]),
        "branching": aggregate([x["branching"] for x in results]),
        "results": results,
    }
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--provider-env", action="store_true", help="Provider environment is inherited and never read by this harness.")
    args = parser.parse_args()
    asyncio.run(main(args.fixtures, args.repeat))

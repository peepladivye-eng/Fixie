"""Run baseline and branching evaluations, safely retaining completed instances."""
from __future__ import annotations

import asyncio
import argparse
import os
import json
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if os.getenv("FIXIE_FORCE_FAKE_RUNNER") == "1":
    from app.fake_runner import run_agent
else:
    try:
        from app.agent.runner import run_agent  # type: ignore[import-not-found]
    except ImportError:
        from app.fake_runner import run_agent

ROOT = Path(__file__).parent
OUTPUT = ROOT / "eval.json"


async def one_run(source: str, options: dict[str, int]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    started = time.perf_counter()

    async def emit(event_type: str, data: dict[str, Any]) -> None:
        events.append({"type": event_type, "data": data})

    await run_agent(source, emit, options)
    models: dict[str, dict[str, float]] = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
    for event in events:
        if event["type"] == "llm.usage":
            usage, bucket = event["data"], models[event["data"]["model"]]
            bucket["input_tokens"] += usage["input_tokens"]
            bucket["output_tokens"] += usage["output_tokens"]
            bucket["cost_usd"] += usage["cost_usd"]
    finished = next((event for event in reversed(events) if event["type"] == "run.finished"), {"data": {"status": "failed"}})
    return {"resolved": finished["data"].get("status") == "success", "rounds": sum(e["type"] == "step.started" and e["data"]["step"] == "branch" for e in events), "cost_usd": sum(v["cost_usd"] for v in models.values()), "seconds": time.perf_counter() - started, "per_model": dict(models)}


def aggregate(items: list[dict[str, Any]]) -> dict[str, Any]:
    model: dict[str, dict[str, float]] = defaultdict(lambda: {"input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
    for item in items:
        for name, usage in item["per_model"].items():
            for key in model[name]: model[name][key] += usage[key]
    return {"resolved": sum(x["resolved"] for x in items), "rounds": sum(x["rounds"] for x in items), "cost_usd": sum(x["cost_usd"] for x in items), "seconds": sum(x["seconds"] for x in items), "per_model": dict(model)}


async def main(fixtures: bool = False, repeat: int = 1) -> None:
    if fixtures:
        if __import__("os").getenv("FIXIE_ALLOW_LOCAL") != "1":
            raise RuntimeError("fixtures require FIXIE_ALLOW_LOCAL=1")
        instances = [{"id": item.name, "source": f"fixture:{item.name}"} for item in sorted((ROOT / "fixtures").iterdir()) if item.is_dir()]
    else:
        instances = json.loads((ROOT / "instances.json").read_text(encoding="utf-8"))
    previous = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else {"results": []}
    completed = {item["id"]: item for item in previous.get("results", [])}
    semaphore = asyncio.Semaphore(4)

    async def evaluate(instance: dict[str, str]) -> dict[str, Any]:
        if instance["id"] in completed: return completed[instance["id"]]
        async with semaphore:
            return {"id": instance["id"], "baseline": await one_run(instance["source"], {"k_branches": 1, "max_rounds": 2}), "branching": await one_run(instance["source"], {"k_branches": 3, "max_rounds": 2})}

    expanded = [{**item, "id": f"{item['id']}#{number}"} for item in instances for number in range(repeat)]
    results = await asyncio.gather(*(evaluate(item) for item in expanded))
    report = {"synthetic": run_agent.__module__.endswith("fake_runner"), "instances_total": len(results), "baseline": aggregate([x["baseline"] for x in results]), "branching": aggregate([x["branching"] for x in results]), "results": results}
    OUTPUT.write_text(json.dumps(report, indent=2), encoding="utf-8")


def grade_with_hidden_tests(fixture_name: str, diff: str) -> bool:
    """Grade a candidate patch against hidden tests in an isolated fresh copy."""
    import shutil
    import subprocess
    import tempfile

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


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", action="store_true")
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--provider-env", action="store_true", help="Provider environment is inherited and never read by this harness.")
    args = parser.parse_args()
    asyncio.run(main(args.fixtures, args.repeat))

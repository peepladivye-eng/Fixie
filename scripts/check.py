"""One verification command: event validator + pytest (+ frontend lint/build with --frontend)."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(label: str, cmd: list[str], cwd: Path = ROOT) -> bool:
    print(f"\n== {label}: {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=cwd).returncode == 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--frontend", action="store_true", help="also run frontend lint and build")
    args = parser.parse_args()
    py = sys.executable
    import os
    os.environ["PATH"] = f"{Path(py).parent}{os.pathsep}{os.environ.get('PATH', '')}"
    results = {
        "validate sample replay": run("validate", [py, "-m", "backend.tools.validate_events", "replays/sample_run.jsonl"]),
        "pytest": run("pytest", [py, "-m", "pytest", "-q"]),
    }
    if args.frontend:
        npm = shutil.which("npm")
        if npm is None:
            results["frontend (npm not found)"] = False
        else:
            frontend = ROOT / "frontend"
            results["frontend lint"] = run("lint", [npm, "run", "lint"], frontend)
            results["frontend build"] = run("build", [npm, "run", "build"], frontend)
    print("\n== summary")
    for name, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

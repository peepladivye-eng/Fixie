"""Day 0 smoke checks for Fixie backend.

Verifies:
1. Environment variables loaded cleanly with safe zero-cost fallbacks.
2. SQLite store initializes schema without errors.
3. Contracts schema and sample replay exist and validate.
4. FastAPI app mounts and health check responds.
"""

import sys
from pathlib import Path
from backend.app.main import app, get_health
from backend.app.store import RunStore
from backend.tools.validate_events import validate_file

REPO_ROOT = Path(__file__).resolve().parent.parent


def run_smoke_checks() -> bool:
    print("Running Day 0 Smoke Checks...")

    # 1. Health check
    health = get_health()
    assert health.status == "ok", f"Health status not ok: {health}"
    assert health.live_enabled is False, "Live execution should be disabled by default (zero-cost)"
    print("  [PASS] Health check verified")

    # 2. SQLite store init
    store = RunStore(":memory:")
    assert store is not None
    print("  [PASS] SQLite store initialized")

    # 3. Sample replay validation
    sample_replay = REPO_ROOT / "replays" / "sample_run.jsonl"
    assert sample_replay.exists(), f"Sample replay not found at {sample_replay}"
    ok, errors = validate_file(str(sample_replay))
    if not ok:
        print(f"  [FAIL] Validation errors: {errors}", file=sys.stderr)
        return False
    print("  [PASS] contracts/events.schema.json & replays/sample_run.jsonl verified")

    print("All Day 0 smoke checks passed.")
    return True


if __name__ == "__main__":
    success = run_smoke_checks()
    sys.exit(0 if success else 1)

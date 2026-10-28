"""validate_events: Validates a JSONL event file against contracts/events.schema.json.

Usage:
    python -m backend.tools.validate_events <path/to/file.jsonl>

Exits 0 on success, 1 on any validation error.
"""

import json
import sys
from pathlib import Path

import jsonschema

# Resolve schema path relative to repo root regardless of cwd
_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCHEMA_PATH = _REPO_ROOT / "contracts" / "events.schema.json"


def load_schema() -> dict:
    with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_file(jsonl_path: str) -> tuple[bool, list[str]]:
    """Validate all events in a JSONL file.

    Returns (ok: bool, errors: list[str]).
    Checks:
      1. Each line is valid JSON.
      2. Each event validates against the schema.
      3. seq values are strictly ascending starting from 0.
    """
    schema = load_schema()
    validator = jsonschema.Draft7Validator(schema)

    errors: list[str] = []
    prev_seq: int | None = None

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            raw = raw.strip()
            if not raw:
                continue

            # 1. Parse JSON
            try:
                event = json.loads(raw)
            except json.JSONDecodeError as exc:
                errors.append(f"Line {lineno}: JSON parse error: {exc}")
                continue

            # 2. Schema validation
            schema_errors = list(validator.iter_errors(event))
            for err in schema_errors:
                errors.append(f"Line {lineno} (seq={event.get('seq', '?')}): {err.message}")

            # 3. Sequence order check
            seq = event.get("seq")
            if isinstance(seq, int):
                if prev_seq is None and seq != 0:
                    errors.append(
                        f"Line {lineno}: First event seq must be 0, got {seq}"
                    )
                elif prev_seq is not None and seq != prev_seq + 1:
                    errors.append(
                        f"Line {lineno}: seq out of order — expected {prev_seq + 1}, got {seq}"
                    )
                prev_seq = seq

    return (len(errors) == 0), errors


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m backend.tools.validate_events <file.jsonl>", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    ok, errors = validate_file(path)

    if ok:
        print(f"OK: All events in '{path}' are valid.")
        sys.exit(0)
    else:
        print(f"FAIL: Validation failed for '{path}' with {len(errors)} error(s):")
        for err in errors:
            print(f"  {err}")
        sys.exit(1)


if __name__ == "__main__":
    main()

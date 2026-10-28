"""Tests for backend.tools.validate_events."""

import json
import pytest
from pathlib import Path
from backend.tools.validate_events import validate_file

_REPLAYS = Path(__file__).resolve().parents[2] / "replays"
_SAMPLE = _REPLAYS / "sample_run.jsonl"


def test_sample_run_is_valid():
    """The bundled sample replay must pass schema validation and seq ordering."""
    ok, errors = validate_file(str(_SAMPLE))
    assert ok, f"Validation errors:\n" + "\n".join(errors)


def test_bad_json_line(tmp_path):
    """A line with invalid JSON is reported as an error."""
    bad = tmp_path / "bad.jsonl"
    bad.write_text("not json\n")
    ok, errors = validate_file(str(bad))
    assert not ok
    assert any("JSON parse error" in e for e in errors)


def test_missing_required_field(tmp_path):
    """An event missing 'run_id' should fail schema validation."""
    event = {
        # run_id missing
        "seq": 0,
        "ts": "2026-10-28T08:00:00.000Z",
        "type": "run.started",
        "data": {"issue_title": "Test", "repo": "org/repo", "mode": "replay"},
    }
    f = tmp_path / "missing_field.jsonl"
    f.write_text(json.dumps(event) + "\n")
    ok, errors = validate_file(str(f))
    assert not ok
    assert any("run_id" in e for e in errors)


def test_seq_must_start_at_zero(tmp_path):
    """Events must begin at seq=0."""
    event = {
        "run_id": "r1",
        "seq": 1,  # Should be 0
        "ts": "2026-10-28T08:00:00.000Z",
        "type": "run.started",
        "data": {"issue_title": "Test", "repo": "org/repo", "mode": "replay"},
    }
    f = tmp_path / "wrong_start.jsonl"
    f.write_text(json.dumps(event) + "\n")
    ok, errors = validate_file(str(f))
    assert not ok
    assert any("seq must be 0" in e for e in errors)


def test_seq_must_be_ascending(tmp_path):
    """Events with non-consecutive seq numbers must be flagged."""
    events = [
        {
            "run_id": "r1",
            "seq": 0,
            "ts": "2026-10-28T08:00:00.000Z",
            "type": "run.started",
            "data": {"issue_title": "T", "repo": "org/repo", "mode": "replay"},
        },
        {
            "run_id": "r1",
            "seq": 5,  # Gap: expected 1
            "ts": "2026-10-28T08:00:01.000Z",
            "type": "run.finished",
            "data": {"status": "success", "total_cost_usd": 0.01, "total_seconds": 5.0},
        },
    ]
    f = tmp_path / "gap_seq.jsonl"
    f.write_text("\n".join(json.dumps(e) for e in events) + "\n")
    ok, errors = validate_file(str(f))
    assert not ok
    assert any("out of order" in e for e in errors)


def test_unknown_event_type(tmp_path):
    """An event with an unsupported type must fail schema validation."""
    event = {
        "run_id": "r1",
        "seq": 0,
        "ts": "2026-10-28T08:00:00.000Z",
        "type": "unknown.event",
        "data": {},
    }
    f = tmp_path / "bad_type.jsonl"
    f.write_text(json.dumps(event) + "\n")
    ok, errors = validate_file(str(f))
    assert not ok


def test_empty_file(tmp_path):
    """An empty JSONL file has no events and should be considered valid."""
    f = tmp_path / "empty.jsonl"
    f.write_text("")
    ok, errors = validate_file(str(f))
    assert ok
    assert errors == []

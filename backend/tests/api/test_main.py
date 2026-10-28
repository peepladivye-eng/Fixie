import importlib
import json
import os
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.tools.validate_events import load_schema
import jsonschema


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    monkeypatch.setenv("FIXIE_FORCE_FAKE_RUNNER", "1")
    monkeypatch.setenv("LIVE_ENABLED", "false")
    monkeypatch.setenv("FIXIE_DAILY_LIVE_CAP", "25")
    import app.main
    module = importlib.reload(app.main)
    with TestClient(module.app) as test_client:
        yield test_client


def wait_for_finished(client, run_id):
    for _ in range(100):
        run = client.get(f"/runs/{run_id}").json()
        if run["status"] != "running":
            return run
        time.sleep(0.01)
    raise AssertionError("run did not finish")


def test_live_disabled_by_default(client):
    """When LIVE_ENABLED is false (the default), POST /runs in live mode yields 429 LIVE_PAUSED."""
    resp = client.post("/runs", json={"source": "https://github.com/acme/demo/issues/1", "mode": "live"})
    assert resp.status_code == 429
    body = resp.json()
    assert body["error"] == "LIVE_PAUSED"
    assert "disabled" in body["message"]


def test_live_run_and_contract_validation(tmp_path, monkeypatch):
    """Fake-live contract test: starts fake live run, collects SSE events, validates each against schema."""
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    monkeypatch.setenv("FIXIE_FORCE_FAKE_RUNNER", "1")
    monkeypatch.setenv("LIVE_ENABLED", "true")
    monkeypatch.setenv("FIXIE_DAILY_LIVE_CAP", "10")
    import app.main
    module = importlib.reload(app.main)

    with TestClient(module.app) as client:
        created = client.post("/runs", json={"source": "https://github.com/acme/demo/issues/1", "mode": "live"})
        assert created.status_code == 201
        run_id = created.json()["run_id"]

        run = wait_for_finished(client, run_id)
        assert run["status"] == "success"
        assert run["id"] == run_id

        # Stream SSE events
        sse_resp = client.get(f"/runs/{run_id}/events")
        assert sse_resp.status_code == 200

        schema = load_schema()
        validator = jsonschema.Draft7Validator(schema)

        events = []
        for line in sse_resp.text.split("\n"):
            if line.startswith("data: "):
                event_data = json.loads(line[6:])
                events.append(event_data)
                errors = list(validator.iter_errors(event_data))
                assert len(errors) == 0, f"Schema error on {event_data}: {[e.message for e in errors]}"

        assert len(events) > 0
        assert events[0]["type"] == "run.started"
        assert events[-1]["type"] == "run.finished"


def test_replay_serves_all_56_events_and_validates(tmp_path, monkeypatch):
    """Replay of real sample_run.jsonl serves all 56 events in seq order and all pass schema validation."""
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    import app.main
    module = importlib.reload(app.main)

    with TestClient(module.app) as client:
        created = client.post("/runs", json={"source": "sample_run.jsonl", "mode": "replay", "speed": 1000.0})
        assert created.status_code == 201
        run_id = created.json()["run_id"]

        run = wait_for_finished(client, run_id)
        assert run["status"] == "success"

        sse_resp = client.get(f"/runs/{run_id}/events")
        assert sse_resp.status_code == 200

        schema = load_schema()
        validator = jsonschema.Draft7Validator(schema)

        events = []
        for line in sse_resp.text.split("\n"):
            if line.startswith("data: "):
                event_data = json.loads(line[6:])
                events.append(event_data)
                errors = list(validator.iter_errors(event_data))
                assert len(errors) == 0, f"Schema validation error: {errors}"

        assert len(events) == 56
        assert [e["seq"] for e in events] == list(range(56))
        assert events[-1]["type"] == "run.finished"


def test_showcase_matches_json(client):
    resp = client.get("/showcase")
    assert resp.status_code == 200
    catalog = resp.json()
    assert len(catalog) >= 1
    assert catalog[0]["id"] == "run_20261028_parse_duration"


def test_live_cap_at_one(tmp_path, monkeypatch):
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    monkeypatch.setenv("FIXIE_FORCE_FAKE_RUNNER", "1")
    monkeypatch.setenv("LIVE_ENABLED", "true")
    monkeypatch.setenv("FIXIE_DAILY_LIVE_CAP", "1")
    import app.main
    module = importlib.reload(app.main)

    with TestClient(module.app) as client:
        assert client.get("/health").json()["daily_runs_left"] == 1
        first = client.post("/runs", json={"source": "https://github.com/acme/demo/issues/1", "mode": "live"})
        assert first.status_code == 201

        blocked = client.post("/runs", json={"source": "https://github.com/acme/demo/issues/2", "mode": "live"})
        assert blocked.status_code == 429
        assert blocked.json()["error"] == "LIVE_PAUSED"


def test_invalid_source_returns_422_with_error_shape(client):
    response = client.post("/runs", json={"source": "invalid://not a source", "mode": "replay"})
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert "message" in data


def test_missing_replay_returns_404_with_error_shape(client):
    response = client.post("/runs", json={"source": "nonexistent_file.jsonl", "mode": "replay"})
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "NOT_FOUND"


def test_run_finished_follows_run_error(tmp_path, monkeypatch):
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    monkeypatch.setenv("LIVE_ENABLED", "true")
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")

    import app.main
    module = importlib.reload(app.main)

    # Mock run_agent to raise an exception
    async def failing_agent(source, emit, options):
        await emit("run.started", {"issue_title": "Fail test", "repo": "r", "mode": "live"})
        raise RuntimeError("Something exploded")

    monkeypatch.setattr(module, "run_agent", failing_agent)

    with TestClient(module.app) as client:
        created = client.post("/runs", json={"source": "fixture:parse_duration", "mode": "live"})
        assert created.status_code == 201
        run_id = created.json()["run_id"]

        wait_for_finished(client, run_id)
        sse_resp = client.get(f"/runs/{run_id}/events")
        events = [json.loads(line[6:]) for line in sse_resp.text.split("\n") if line.startswith("data: ")]

        types = [e["type"] for e in events]
        assert "run.error" in types
        assert "run.finished" in types
        # run.finished MUST come after run.error
        error_idx = types.index("run.error")
        finished_idx = types.index("run.finished")
        assert finished_idx > error_idx

import importlib
import time

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    monkeypatch.setenv("FIXIE_FORCE_FAKE_RUNNER", "1")
    monkeypatch.setenv("FIXIE_DAILY_LIVE_CAP", "25")
    import app.main
    module = importlib.reload(app.main)
    with TestClient(module.app) as test_client:
        yield test_client


def wait_for_finished(client, run_id):
    for _ in range(100):
        run = client.get(f"/runs/{run_id}").json()
        if run["status"] != "running": return run
        time.sleep(0.01)
    raise AssertionError("run did not finish")


def test_live_run_and_sse_resume(client):
    created = client.post("/runs", json={"source": "issue body", "mode": "live"})
    assert created.status_code == 200
    run_id = created.json()["run_id"]
    run = wait_for_finished(client, run_id)
    assert run["status"] == "success"
    assert [event["seq"] for event in run["events"]] == list(range(len(run["events"])))
    assert run["events"][-1]["type"] == "run.finished"
    response = client.get(f"/runs/{run_id}/events", headers={"Last-Event-ID": "1"})
    assert response.status_code == 200
    assert 'id: 2' in response.text
    assert 'event: run.finished' in response.text


def test_replay_health_eval_and_live_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    monkeypatch.setenv("FIXIE_FORCE_FAKE_RUNNER", "1")
    monkeypatch.setenv("FIXIE_DAILY_LIVE_CAP", "1")
    import app.main
    module = importlib.reload(app.main)
    with TestClient(module.app) as client:
        assert client.get("/health").json()["daily_runs_left"] == 1
        first = client.post("/runs", json={"source": "one", "mode": "live"})
        assert first.status_code == 200
        blocked = client.post("/runs", json={"source": "two", "mode": "live"})
        assert blocked.status_code == 429
        assert blocked.json()["detail"]["code"] == "LIVE_PAUSED"
        replay = client.post("/runs", json={"source": "missing.jsonl", "mode": "replay"})
        assert replay.status_code == 200
        replay_run = wait_for_finished(client, replay.json()["run_id"])
        assert replay_run["mode"] == "replay"
        assert client.get("/eval/summary").json()["synthetic"] is True

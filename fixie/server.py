from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .models import CandidatePatch, Issue
from .orchestrator import FixieOrchestrator
from .providers import FakePullRequestProvider, FakeSandboxProvider


def default_candidates() -> list[CandidatePatch]:
    """Deterministic local candidates; replace behind a verified generation interface."""
    return [
        CandidatePatch("minimal", "# FIXIE_PASS\n# minimal candidate\n", "Apply the smallest safe parser fix."),
        CandidatePatch("alternative", "# candidate under evaluation\n", "Alternative parser fix for comparison."),
    ]


def run_issue(payload: dict) -> dict:
    issue = Issue.from_dict(payload)
    report = FixieOrchestrator(FakeSandboxProvider(), FakePullRequestProvider()).run(issue, default_candidates())
    return report.as_dict()


class FixieHandler(BaseHTTPRequestHandler):
    server_version = "Fixie/0.1"

    def _reply(self, status: HTTPStatus, body: dict) -> None:
        content = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
        if self.path == "/health":
            self._reply(HTTPStatus.OK, {"ok": True, "provider_mode": "fake"})
        else:
            self._reply(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802 - stdlib callback name
        if self.path != "/runs":
            self._reply(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > 1_000_000:
                raise ValueError("body must be between 1 and 1,000,000 bytes")
            payload = json.loads(self.rfile.read(content_length))
            self._reply(HTTPStatus.CREATED, run_issue(payload))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            self._reply(HTTPStatus.BAD_REQUEST, {"error": str(error)})

    def log_message(self, format: str, *args) -> None:
        # Keep CLI output concise; production logging is TODO(VERIFY).
        return


def serve(port: int = 8080) -> None:
    with ThreadingHTTPServer(("127.0.0.1", port), FixieHandler) as server:
        print(f"Fixie fake-provider server listening at http://127.0.0.1:{port}")
        server.serve_forever()

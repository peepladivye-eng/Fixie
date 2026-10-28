"""Main agent orchestrator loop for Fixie.

Executes steps 1-7:
1. Ingest Issue & Source
2. Triage & Strategy Plan
3. Reproduce in Sandbox
4. Diagnose Root Cause
5. Branch & Speculative Patching
6. Parallel Verification
7. Winner Selection & Delivery
"""

from typing import AsyncGenerator, Dict, Any


class AgentLoop:
    """Orchestrates triage, reproduction, speculative branching, and delivery."""

    def __init__(self, run_id: str, source: str, mode: str = "replay"):
        self.run_id = run_id
        self.source = source
        self.mode = mode

    async def run(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Execute agent workflow emitting contract-compliant event dicts."""
        # TODO(VERIFY): Prompt 1 backend lane orchestrator implementation
        yield {
            "run_id": self.run_id,
            "seq": 0,
            "ts": "2026-10-28T14:00:00Z",
            "type": "run.started",
            "data": {
                "issue_title": "Issue Ingestion",
                "repo": "sample-repo",
                "mode": self.mode,
            },
        }

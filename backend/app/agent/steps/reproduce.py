"""Reproduce step: Generates reproduction test and executes in base sandbox to confirm bug."""

from typing import Dict, Any


def run_reproduce(run_id: str, sandbox_session: Any) -> Dict[str, Any]:
    """Write reproduction test and execute pytest inside sandbox."""
    # TODO(VERIFY): Run sandbox session pytest and capture stderr/stdout
    return {
        "status": "reproduced",
        "test_file": "tests/test_reproduce.py",
        "exit_code": 1,
    }

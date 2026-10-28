"""Reproduction step: execute visible tests and capture baseline failure."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable

from app.agent.output import parse_pytest_failures
from app.sandbox import LocalSandbox

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]


class ReproductionError(RuntimeError):
    """Raised when the issue reproduction step fails or tests unexpectedly pass."""

    def __init__(self, code: str = "NOT_REPRODUCED", message: str = ""):
        super().__init__(message or code)
        self.code = code


async def run_reproduce(
    sandbox: LocalSandbox,
    test_command: str,
    emit: Emit | None = None,
) -> tuple[dict[str, str], Path]:
    """Execute test_command in sandbox.

    If tests PASS (returncode == 0), emits run.error NOT_REPRODUCED and raises ReproductionError.
    If tests fail, returns compact failure summary and checkpoint B path.
    """
    result = sandbox.run(test_command)
    output_text = (result.stdout or "") + "\n" + (result.stderr or "")

    if result.returncode == 0:
        if emit is not None:
            await emit(
                "run.error",
                {"code": "NOT_REPRODUCED", "message": "Visible tests passed; bug could not be reproduced."},
            )
        raise ReproductionError("NOT_REPRODUCED", "Visible tests passed unexpectedly")

    summary = parse_pytest_failures(output_text)
    checkpoint_b = sandbox.checkpoint()
    return summary, checkpoint_b

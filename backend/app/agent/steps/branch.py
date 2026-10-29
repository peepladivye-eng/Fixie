"""Branch round execution: parallel candidates, streaming chunks, and loser cancellation."""
from __future__ import annotations

import asyncio
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.agent.runner import validate_diff
from app.agent.scoring import calculate_patch_score
from app.llm import ChatClient
from app.sandbox import LocalSandbox

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _sanitize_keys(text: str) -> str:
    """Remove any text that looks like a secret API key or token."""
    for key in ("GEMINI_API_KEY", "NEBIUS_API_KEY", "NVIDIA_API_KEY", "GITHUB_TOKEN"):
        val = os.getenv(key)
        if val and len(val) >= 8:
            text = text.replace(val, "[REDACTED]")
    text = re.sub(r"AIza[0-9A-Za-z-_]{35}", "[REDACTED]", text)
    text = re.sub(r"sk-[A-Za-z0-9-_]{20,}", "[REDACTED]", text)
    text = re.sub(r"(?i)(?:bearer\s+)[A-Za-z0-9_\-\.]{16,}", "Bearer [REDACTED]", text)
    text = re.sub(r"(?i)(api[_-]?key|token|secret)[\s:=]+([A-Za-z0-9_\-\.]{12,})", r"\1=[REDACTED]", text)
    return text


def get_strategies_for_round(round_number: int, showcase: bool = False, baseline: bool = False) -> list[str]:
    """Return strategy labels for round_number (1-indexed) or showcase mode."""
    if baseline:
        return ["patch"]
    if showcase or round_number >= 2:
        return ["minimal", "root-cause", "defensive"]
    return ["patch", "patch_alt"]


def _load_prompt(strategy: str, issue_text: str, failure_summary: str = "", previous_diff: str = "") -> str:
    """Build a prompt string for the given strategy.

    On retry sends only failure summary and previous diff — never the full conversation.
    """
    if failure_summary and previous_diff:
        return (
            f"Previous patch failed tests:\n{failure_summary}\n\n"
            f"Previous Diff:\n{previous_diff}\n\n"
            'Return only JSON matching: {"diff": string, "summary": string} with a corrected unified diff.'
        )

    prompt_file = PROMPTS_DIR / f"{strategy.replace('-', '_')}.txt"
    if prompt_file.is_file():
        template = prompt_file.read_text(encoding="utf-8")
        try:
            return template.format(issue=issue_text)
        except Exception:
            return template.replace("{issue}", issue_text)

    return strategy


async def run_branch_round(
    base_sandbox: LocalSandbox,
    strategies: list[str],
    client: ChatClient,
    test_command: str,
    issue_text: str,
    root_cause: str,
    context: str,
    emit: Emit,
    failure_summary: str = "",
    previous_diff: str = "",
) -> dict[str, Any]:
    """Run K candidates in parallel, cancel losers as soon as one wins."""
    import shutil
    for old_fork in base_sandbox.root.glob("fork-*"):
        if old_fork.is_dir():
            shutil.rmtree(old_fork, ignore_errors=True)

    k = len(strategies)
    forks = base_sandbox.fork(k)

    branch_meta = [{"id": f"candidate-{i + 1}", "strategy": s} for i, s in enumerate(strategies)]
    await emit("branch.forked", {"branches": branch_meta})

    completed_results: list[dict[str, Any]] = []
    cancelled_ids: list[str] = []

    async def execute_branch(index: int, strategy: str, sandbox: LocalSandbox) -> dict[str, Any]:
        branch_id = f"candidate-{index + 1}"
        prompt = _load_prompt(strategy, issue_text, failure_summary, previous_diff)
        if context and not (failure_summary and previous_diff):
            prompt += f"\n\nContext:\n{context}\n\nRoot Cause:\n{root_cause}"

        # Ask model for patch — this is the longest await; cancellation hits here
        try:
            chat_result = await client.chat("patch", prompt)
            raw_reply = chat_result.text.strip() if hasattr(chat_result, "text") else str(chat_result).strip()
        except Exception as exc:
            reason = f"model call failed: {exc}"
            await emit("terminal.chunk", {"stream": "stderr", "text": reason, "branch_id": branch_id})
            await emit(
                "branch.result",
                {
                    "branch_id": branch_id,
                    "tests_passed": False,
                    "diff_lines": 0,
                    "sandbox_seconds": 0.0,
                    "score": 0.0,
                },
            )
            return {
                "branch_id": branch_id,
                "strategy": strategy,
                "tests_passed": False,
                "diff_lines": 0,
                "sandbox_seconds": 0.0,
                "score": 0.0,
                "sort_key": (-1, 0, 0),
                "diff": "",
                "status": "rejected",
            }

        sanitized_reply = _sanitize_keys(raw_reply)
        raw_diff = ""
        parse_err: str | None = None
        try:
            parsed = json.loads(raw_reply)
            if isinstance(parsed, dict):
                raw_diff = parsed.get("diff", "")
                if not raw_diff:
                    parse_err = "missing 'diff' in json response"
            else:
                raw_diff = raw_reply
        except Exception:
            raw_diff = raw_reply

        diff = ""
        diff_valid = False
        val_err = parse_err
        if not val_err:
            try:
                diff = validate_diff(raw_diff)
                diff_valid = True
            except ValueError as exc:
                val_err = str(exc)

        if not diff_valid:
            # Status: "rejected" when model reply is not parseable or validate_diff fails
            err_msg = f"invalid diff: {val_err}\n{sanitized_reply[:400]}"
            await emit("terminal.chunk", {"stream": "stderr", "text": err_msg, "branch_id": branch_id})
            await emit(
                "branch.result",
                {
                    "branch_id": branch_id,
                    "tests_passed": False,
                    "diff_lines": 0,
                    "sandbox_seconds": 0.0,
                    "score": 0.0,
                },
            )
            return {
                "branch_id": branch_id,
                "strategy": strategy,
                "tests_passed": False,
                "diff_lines": 0,
                "sandbox_seconds": 0.0,
                "score": 0.0,
                "sort_key": (-1, 0, 0),
                "diff": "",
                "status": "rejected",
            }

        # Apply patch and run tests in worker thread so subprocesses don't block event loop
        apply_res = await asyncio.to_thread(sandbox.apply_diff, diff)
        diff_lines = len(diff.splitlines())

        t0 = time.monotonic()
        test_res = await asyncio.to_thread(sandbox.run, test_command)
        sandbox_seconds = time.monotonic() - t0
        output = (test_res.stdout or "") + (test_res.stderr or "")
        await emit("terminal.chunk", {"stream": "stdout", "text": output, "branch_id": branch_id})

        # Tests passed if apply succeeded (or was test diff) and test command returned 0
        tests_passed = (test_res.returncode == 0) and (apply_res.returncode == 0 or test_command.startswith("python -c"))

        if not tests_passed:
            # Status: "fail" when patch applies but tests fail
            if apply_res.returncode != 0:
                reason = f"patch apply failed: {(apply_res.stderr or apply_res.stdout).strip()}"
            else:
                reason = f"tests failed with exit code {test_res.returncode}"
            err_msg = f"{reason}\n{sanitized_reply[:400]}"
            await emit("terminal.chunk", {"stream": "stderr", "text": err_msg, "branch_id": branch_id})

        score, sort_key = calculate_patch_score(
            tests_passed=tests_passed,
            diff_lines=diff_lines,
            sandbox_seconds=sandbox_seconds,
        )

        await emit(
            "branch.result",
            {
                "branch_id": branch_id,
                "tests_passed": tests_passed,
                "diff_lines": diff_lines,
                "sandbox_seconds": round(sandbox_seconds, 4),
                "score": score,
            },
        )

        return {
            "branch_id": branch_id,
            "strategy": strategy,
            "tests_passed": tests_passed,
            "diff_lines": diff_lines,
            "sandbox_seconds": round(sandbox_seconds, 4),
            "score": score,
            "sort_key": sort_key,
            "diff": diff,
            "status": "pass" if tests_passed else "fail",
        }

    # Create all tasks; store refs for cross-cancellation
    tasks: list[asyncio.Task] = [
        asyncio.create_task(execute_branch(i, strat, forks[i]))
        for i, strat in enumerate(strategies)
    ]

    winner_found = False

    # Process completions in order of finishing using asyncio.wait
    pending: set[asyncio.Task] = set(tasks)
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            # Find this task's index
            idx = tasks.index(task)
            branch_id = f"candidate-{idx + 1}"

            if task.cancelled():
                if branch_id not in cancelled_ids:
                    cancelled_ids.append(branch_id)
                    await emit("branch.cancelled", {"branch_id": branch_id})
                continue

            exc = task.exception()
            if exc is not None:
                continue

            res = task.result()
            completed_results.append(res)

            # If this branch passes and no winner yet, cancel all pending tasks
            if res["tests_passed"] and not winner_found:
                winner_found = True
                for other_idx, other_task in enumerate(tasks):
                    other_branch_id = f"candidate-{other_idx + 1}"
                    if other_task in pending and not other_task.done():
                        other_task.cancel()

    # Collect any remaining cancellations that weren't caught above
    for idx, task in enumerate(tasks):
        branch_id = f"candidate-{idx + 1}"
        if task.cancelled() and branch_id not in cancelled_ids:
            cancelled_ids.append(branch_id)
            await emit("branch.cancelled", {"branch_id": branch_id})

    # Determine and announce winner
    winner = None
    passing = [r for r in completed_results if r["tests_passed"]]
    if passing:
        winner = max(passing, key=lambda item: item["sort_key"])
        await emit("branch.winner", {"branch_id": winner["branch_id"]})

    return {
        "results": completed_results,
        "winner": winner,
        "cancelled": cancelled_ids,
    }

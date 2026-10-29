"""Branch round execution: parallel candidates, streaming chunks, and loser cancellation."""
from __future__ import annotations

import asyncio
import difflib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.agent.json_output import async_validated_response
from app.agent.runner import Edit, Patch, validate_diff
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
    return re.sub(r"(?i)(api[_-]?key|token|secret)[\s:=]+([A-Za-z0-9_\-\.]{12,})", r"\1=[REDACTED]", text)


def is_test_file(path: str, repro_test: str | None = None) -> bool:
    """Return True if path points to visible test files protected by the integrity rule."""
    norm = path.replace("\\", "/").lstrip("/")
    if repro_test and norm == repro_test.replace("\\", "/").lstrip("/"):
        return False
    parts = Path(norm).parts
    name = Path(norm).name
    return (
        "tests" in parts
        or norm.startswith("tests/")
        or (name.startswith("test_") and name.endswith(".py"))
        or name.endswith("_test.py")
        or name == "conftest.py"
    )


def normalise_diff_headers(diff: str) -> str:
    """Ensure repository-relative unified diff headers have a/ and b/ prefixes."""
    new_lines = []
    for line in diff.splitlines():
        if line.startswith("--- ") and not line.startswith(("--- a/", "--- /dev/null")):
            raw = line[4:].strip().removeprefix("./")
            new_lines.append(f"--- a/{raw}" if not raw.startswith("/") else line)
        elif line.startswith("+++ ") and not line.startswith(("+++ b/", "+++ /dev/null")):
            raw = line[4:].strip().removeprefix("./")
            new_lines.append(f"+++ b/{raw}" if not raw.startswith("/") else line)
        else:
            new_lines.append(line)
    return "\n".join(new_lines) + ("\n" if diff.endswith("\n") else "")


def get_strategies_for_round(round_number: int, showcase: bool = False, baseline: bool = False) -> list[str]:
    if baseline:
        return ["patch"]
    if showcase or round_number >= 2:
        return ["minimal", "root-cause", "defensive"]
    return ["patch", "patch_alt"]


def _load_prompt(strategy: str, issue_text: str, failure_summary: str = "", previous_diff: str = "") -> str:
    if failure_summary and previous_diff:
        return (
            f"Previous patch failed tests:\n{failure_summary}\n\nPrevious Diff:\n{previous_diff}\n\n"
            'Return only JSON: {"edits": [{"path": string, "old": string, "new": string}], "summary": string}, '
            'where "old" is an exact snippet that appears exactly once in the file at "path" (relative to the repo root) and "new" replaces it.'
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
    repro_test_file: str | None = None,
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

        latest_raw_reply = ""

        async def ask_model(p: str) -> str:
            nonlocal latest_raw_reply
            chat_result = await client.chat("patch", p)
            latest_raw_reply = chat_result.text.strip() if hasattr(chat_result, "text") else str(chat_result).strip()
            return latest_raw_reply

        async def reject(reason: str) -> dict[str, Any]:
            sanitized = _sanitize_keys(latest_raw_reply)
            err_msg = f"invalid diff: {reason}\n{sanitized[:400]}"
            await emit("terminal.chunk", {"stream": "stderr", "text": err_msg, "branch_id": branch_id})
            await emit("branch.result", {"branch_id": branch_id, "tests_passed": False, "diff_lines": 0, "sandbox_seconds": 0.0, "score": 0.0})
            return {"branch_id": branch_id, "strategy": strategy, "tests_passed": False, "diff_lines": 0, "sandbox_seconds": 0.0, "score": 0.0, "sort_key": (-1, 0, 0), "diff": "", "status": "rejected"}

        try:
            patch = await async_validated_response(Patch, ask_model, prompt)
        except Exception as exc:
            return await reject(str(exc))

        diff, diff_lines, apply_ok = "", 0, False
        if patch.edits:
            edits_by_file: dict[str, list[Edit]] = {}
            for edit in patch.edits:
                if is_test_file(edit.path, repro_test=repro_test_file):
                    return await reject(f"integrity rule: modifying test file '{edit.path}' is forbidden")
                norm = edit.path.replace("\\", "/").lstrip("/")
                if ".." in norm or norm.startswith(("/", "\\")):
                    return await reject(f"unsafe file path '{edit.path}'")
                if not (sandbox.workdir / norm).is_file():
                    return await reject(f"file not found: '{edit.path}'")
                edits_by_file.setdefault(norm, []).append(edit)

            diff_parts = []
            for norm, file_edits in edits_by_file.items():
                orig_content = sandbox.read_file(norm)
                current_content = orig_content
                for edit in file_edits:
                    count = current_content.count(edit.old)
                    if count == 0:
                        return await reject(f"snippet 'old' not found in '{edit.path}'")
                    if count > 1:
                        return await reject(f"snippet 'old' appears {count} times (must be unique) in '{edit.path}'")
                    current_content = current_content.replace(edit.old, edit.new, 1)

                sandbox.write_file(norm, current_content)
                part = difflib.unified_diff(
                    orig_content.splitlines(keepends=True),
                    current_content.splitlines(keepends=True),
                    fromfile=f"a/{norm}",
                    tofile=f"b/{norm}",
                )
                diff_parts.extend(part)

            diff = "".join(diff_parts)
            try:
                diff = validate_diff(diff)
            except ValueError as exc:
                return await reject(str(exc))
            diff_lines = len(diff.splitlines())
            apply_ok = True

        elif patch.diff:
            normalized = normalise_diff_headers(patch.diff)
            for line in normalized.splitlines():
                if line.startswith(("--- a/", "+++ b/")):
                    p = line[6:].strip()
                    if is_test_file(p, repro_test=repro_test_file):
                        return await reject(f"integrity rule: modifying test file '{p}' is forbidden")
            try:
                diff = validate_diff(normalized)
            except ValueError as exc:
                return await reject(str(exc))
            diff_lines = len(diff.splitlines())
            apply_res = await asyncio.to_thread(sandbox.apply_diff, diff)
            apply_ok = (apply_res.returncode == 0)

        else:
            return await reject("response must contain 'edits' or 'diff'")

        t0 = time.monotonic()
        test_res = await asyncio.to_thread(sandbox.run, test_command)
        sandbox_seconds = time.monotonic() - t0
        output = (test_res.stdout or "") + (test_res.stderr or "")
        await emit("terminal.chunk", {"stream": "stdout", "text": output, "branch_id": branch_id})

        tests_passed = (test_res.returncode == 0) and (apply_ok or test_command.startswith("python -c"))
        if not tests_passed:
            reason = f"tests failed with exit code {test_res.returncode}"
            sanitized = _sanitize_keys(latest_raw_reply)
            err_msg = f"{reason}\n{sanitized[:400]}"
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

            if res["tests_passed"] and not winner_found:
                winner_found = True
                for other_idx, other_task in enumerate(tasks):
                    if other_task in pending and not other_task.done():
                        other_task.cancel()

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

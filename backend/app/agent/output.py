"""Output processing, truncation, and pytest failure parsing."""
from __future__ import annotations

import re


def truncate_output(text: str, max_head_lines: int = 40, max_tail_lines: int = 60, max_chars: int = 4000) -> str:
    """Truncates output to its first 40 and last 60 lines and at most 4000 chars."""
    if not text:
        return ""
    lines = text.splitlines()
    if len(lines) > (max_head_lines + max_tail_lines):
        head = lines[:max_head_lines]
        tail = lines[-max_tail_lines:]
        truncated_lines = head + [f"... [truncated {len(lines) - max_head_lines - max_tail_lines} lines] ..."] + tail
        text = "\n".join(truncated_lines)

    if len(text) > max_chars:
        half = max_chars // 2 - 20
        text = text[:half] + "\n... [truncated] ...\n" + text[-half:]
    return text


def parse_pytest_failures(output: str) -> dict[str, str]:
    """Parse `pytest -q --tb=short -x` failures in code into a compact summary (test name, assertion, file:line)."""
    summary = {
        "test_name": "unknown_test",
        "assertion": "Test failed",
        "location": "unknown:0",
        "raw_summary": "",
    }
    if not output:
        return summary

    # Look for failed test line: FAILED test_file.py::test_name - AssertionError: ...
    # or short traceback: test_file.py:12: AssertionError: ...
    failed_match = re.search(r"FAILED\s+([^\s:]+::[^\s\-]+)(?:\s+-\s+(.+))?", output)
    if failed_match:
        summary["test_name"] = failed_match.group(1)
        if failed_match.group(2):
            summary["assertion"] = failed_match.group(2).strip()

    loc_match = re.search(r"([a-zA-Z0-9_\-\.\/\\]+\.py):(\d+):\s+(AssertionError.*|ValueError.*|TypeError.*|.*Error.*)", output)
    if loc_match:
        summary["location"] = f"{loc_match.group(1)}:{loc_match.group(2)}"
        if summary["assertion"] == "Test failed":
            summary["assertion"] = loc_match.group(3).strip()

    # Compact one-line raw summary
    summary["raw_summary"] = f"{summary['test_name']} failed at {summary['location']} ({summary['assertion']})"
    return summary

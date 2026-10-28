"""Deterministic scoring function for candidate patches."""
from __future__ import annotations


def calculate_patch_score(
    tests_passed: bool,
    new_failures: int = 0,
    diff_lines: int = 0,
    sandbox_seconds: float = 0.0,
) -> tuple[float, tuple[int, int, int, float]]:
    """Scores a candidate patch purely with deterministic code.

    Rules:
      1. Reproduction test must pass (else score 0.0).
      2. Then rank by fewer new failures, smaller diff, less sandbox time.
      3. Returns (normalized_score in [0.0, 1.0], sort_key tuple for comparison).
    """
    if not tests_passed:
        # If reproduction test fails, score is 0.0
        sort_key = (0, -new_failures, -diff_lines, -sandbox_seconds)
        return 0.0, sort_key

    # Base score for passing tests
    base = 0.70

    # Penalties for new failures (up to -0.5)
    failure_penalty = min(0.50, new_failures * 0.15)

    # Reward for smaller diff (fewer modified lines: diff <= 5 gets +0.25, larger gets less)
    diff_reward = max(0.0, 0.25 - (max(0, diff_lines - 3) * 0.01))

    # Small speed bonus (under 5 seconds gets +0.05)
    speed_reward = max(0.0, 0.05 - (min(5.0, sandbox_seconds) * 0.01))

    score = round(min(1.0, max(0.0, base - failure_penalty + diff_reward + speed_reward)), 4)
    sort_key = (1, -new_failures, -diff_lines, -sandbox_seconds)
    return score, sort_key

"""Diagnose step: Identifies root cause and searches documentation or codebase references."""

from typing import Dict, Any


def run_diagnose(run_id: str, reproduction_output: str) -> Dict[str, Any]:
    """Diagnose root cause and formulate patch hypotheses."""
    # TODO(VERIFY): LLM call with model_tier='super' and optional Tavily search
    return {
        "root_cause": "Unit multiplier logic treats 'h' as 60 minutes instead of 3600 seconds",
        "hypotheses": ["Fix multiplier dict", "Convert unit after parsing"],
    }

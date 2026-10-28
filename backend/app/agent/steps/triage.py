"""Triage step: Ingests issue description, analyzes stack traces, and plans reproduction."""

from typing import Dict, Any


def run_triage(run_id: str, issue_text: str) -> Dict[str, Any]:
    """Analyze issue text and identify suspected modules and test approach."""
    # TODO(VERIFY): LLM call to triage prompt with model_tier='lightning'
    return {
        "status": "ok",
        "suspected_files": ["parser.py"],
        "strategy": "reproduce_failing_unit_test",
    }

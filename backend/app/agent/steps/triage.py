"""Triage step: identify likely relevant repository files using lightning tier."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.agent.context import rank_repo_files
from app.llm import ChatClient


class TriageError(RuntimeError):
    def __init__(self, code: str = "NO_RELEVANT_FILES", message: str = ""):
        super().__init__(message or code)
        self.code = code


Emit = Callable[[str, dict[str, Any]], Awaitable[None]]


async def run_triage(
    repo_dir: Path,
    issue_text: str,
    client: ChatClient | None = None,
    emit: Emit | None = None,
    max_files: int = 8,
) -> list[str]:
    """Triage issue and identify up to max_files likely files.

    Emits run.error NO_RELEVANT_FILES and raises TriageError if none found.
    """
    terms = re.findall(r"[a-zA-Z_][a-zA-Z0-9_]{2,}", issue_text)
    ranked = rank_repo_files(repo_dir, terms)

    if not ranked:
        # Fallback to non-test py files in repository
        ranked = [p for p in repo_dir.rglob("*.py") if "test" not in p.name.lower() and not p.name.startswith(".")]

    if not ranked:
        if emit is not None:
            await emit("run.error", {"code": "NO_RELEVANT_FILES", "message": "No relevant repository files identified."})
        raise TriageError("NO_RELEVANT_FILES", "No relevant repository files found")

    selected = [str(p.relative_to(repo_dir)).replace("\\", "/") for p in ranked[:max_files]]

    # Optionally invoke lightning model if client provided
    if client is not None:
        try:
            await client.chat("triage", f"Issue: {issue_text}\nCandidate files: {json.dumps(selected)}")
        except Exception:
            pass

    return selected

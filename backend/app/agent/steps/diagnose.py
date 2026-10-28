"""Diagnose step: root cause determination with optional cached Tavily search."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.llm import ChatClient
from app.search import TavilySearch

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]


async def run_diagnose(
    issue_text: str,
    failure_summary: dict[str, str] | str,
    context: str,
    client: ChatClient,
    emit: Emit | None = None,
    search_client: TavilySearch | None = None,
) -> str:
    """Determine root cause note using context and failure summary.

    Executes at most one search via app.search.TavilySearch, emitting search.result.
    """
    search_used = False
    failure_str = json.dumps(failure_summary) if isinstance(failure_summary, dict) else str(failure_summary)

    # Check if external module or unexpected exception is named
    external_match = re.search(r"ModuleNotFoundError: No module named '([^']+)'", failure_str)
    if external_match and search_client is not None:
        query = f"python {external_match.group(1)} module usage fix"
        try:
            results = search_client.search(query)
            if emit is not None and results:
                first = results[0] if isinstance(results[0], dict) else {}
                title = str(first.get("title", f"Information about {external_match.group(1)}"))
                url = str(first.get("url", "https://docs.python.org/3/"))
                await emit("search.result", {"query": query, "title": title, "url": url, "used": True})
        except Exception:
            pass

    prompt = (
        f"Issue:\n{issue_text}\n\n"
        f"Failure Summary:\n{failure_str}\n\n"
        f"Relevant Code Context:\n{context}\n\n"
        "Diagnose the root cause of the bug in concise terms."
    )

    result = await client.chat("diagnose", prompt)
    root_cause = result.text.strip()
    try:
        data = json.loads(root_cause)
        if isinstance(data, dict) and "root_cause" in data:
            root_cause = str(data["root_cause"])
    except Exception:
        pass

    return root_cause

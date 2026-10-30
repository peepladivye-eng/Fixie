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

    # One real Tavily search per run when a key is configured
    search_notes = ""
    if search_client is not None and getattr(search_client, "api_key", None):
        match = re.search(r"\b([A-Za-z]+Error)\b[:\s]*([^\n]{0,100})", failure_str)
        source = " ".join(match.groups()) if match else failure_str
        query = re.sub(r"[^A-Za-z0-9_ .:'-]", " ", "python " + source)
        query = re.sub(r"\s+", " ", query).strip()[:180]
        try:
            results = search_client.search(query)
            if results:
                first = results[0] if isinstance(results[0], dict) else {}
                snippet = str(first.get("content", ""))[:400]
                title = str(first.get("title", "Search result"))
                url = str(first.get("url", ""))
                if snippet:
                    search_notes = f"\n\nSearch notes (from {url}):\n{snippet}\n"
                if emit is not None:
                    await emit("search.result", {"query": query, "title": title, "url": url, "used": bool(snippet)})
        except Exception:
            pass

    prompt = (
        f"Issue:\n{issue_text}\n\n"
        f"Failure Summary:\n{failure_str}\n\n"
        f"Relevant Code Context:\n{context}\n\n"
        f"{search_notes}\nDiagnose the root cause of the bug in concise terms."
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

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from pathlib import Path

import httpx


class TavilySearch:
    def __init__(self, api_key: str | None = None, cache_dir: Path | None = None) -> None:
        self.api_key = api_key or os.getenv("TAVILY_API_KEY")
        self.cache_dir = cache_dir or Path(os.getenv("FIXIE_SEARCH_CACHE", Path(tempfile.gettempdir()) / "fixie-search-cache"))

    def search(self, query: str) -> list[dict]:
        key = hashlib.sha256(query.encode("utf-8")).hexdigest()
        cache = self.cache_dir / f"{key}.json"
        if cache.is_file():
            return json.loads(cache.read_text(encoding="utf-8"))
        if not self.api_key:
            raise RuntimeError("TAVILY_API_KEY is required for an uncached Tavily search")
        # TODO(VERIFY): Tavily REST endpoint and payload contract.
        response = httpx.post("https://api.tavily.com/search", json={"api_key": self.api_key, "query": query, "max_results": 3}, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=30.0)
        response.raise_for_status()
        results = response.json().get("results", [])
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(results), encoding="utf-8")
        return results

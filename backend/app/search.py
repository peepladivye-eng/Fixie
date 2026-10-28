"""Search integration abstraction (e.g. Tavily search).

Conforms to contracts/interfaces.md and respects zero-cost rules.
"""

import os
from typing import List, Optional
from pydantic import BaseModel


class SearchResult(BaseModel):
    query: str
    title: str
    url: str
    content: str


class SearchClient:
    """Tavily search client wrapper."""

    def __init__(self):
        self.api_key = os.getenv("TAVILY_API_KEY", "")

    def query(self, query: str, max_results: Optional[int] = 5) -> List[SearchResult]:
        """Execute web/doc search."""
        # TODO(VERIFY): Connect to Tavily client when TAVILY_API_KEY is supplied
        return [
            SearchResult(
                query=query,
                title="Mock Search Result",
                url="https://docs.python-guide.org/snippets/durations",
                content="Duration parsing unit multiplier reference.",
            )
        ]

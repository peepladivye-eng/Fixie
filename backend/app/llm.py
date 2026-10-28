"""LLM client abstraction for Nebius Token Factory / NVIDIA NIM.

Enforces zero-cost development rules: all calls fallback to fake/mock completions
when API keys are not present in environment variables.
"""

import os
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class UsageRecord(BaseModel):
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: Dict[str, Any]


class ChatResponse(BaseModel):
    content: Optional[str] = None
    tool_calls: List[ToolCall] = []
    usage: UsageRecord


class LLMClient:
    """Language model client wrapping Nebius Token Factory / NVIDIA NIM."""

    def __init__(self):
        # Read keys strictly from environment variables; zero-cost fallback if absent
        self.nebius_api_key = os.getenv("NEBIUS_API_KEY", "")
        self.nvidia_api_key = os.getenv("NVIDIA_API_KEY", "")

    def chat(
        self,
        role: str,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        max_tokens: Optional[int] = 1024,
    ) -> ChatResponse:
        """Execute chat completion conforming to contracts/interfaces.md."""
        # TODO(VERIFY): Connect to live Nebius / NVIDIA OpenAI-compatible endpoints when keys exist
        return ChatResponse(
            content="Mock LLM response for role: " + role,
            tool_calls=[],
            usage=UsageRecord(
                model=f"mock-{role}-v1",
                input_tokens=150,
                output_tokens=50,
                cost_usd=0.0015,
            ),
        )

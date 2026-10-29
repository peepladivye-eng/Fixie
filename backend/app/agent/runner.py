from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from pydantic import BaseModel

from app.llm import ChatClient, configured_client
from app.sandbox import LocalSandbox
from .json_output import validated_response

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]
PROMPTS = Path(__file__).with_name("prompts")


class Triage(BaseModel):
    summary: str
    risk: str


class Reproduction(BaseModel):
    command: str
    expected: str


class Diagnosis(BaseModel):
    root_cause: str


class Edit(BaseModel):
    path: str
    old: str
    new: str


class Patch(BaseModel):
    edits: list[Edit] = []
    diff: str = ""
    summary: str = ""


def validate_diff(diff: str) -> str:
    if not diff.startswith("--- a/") or "\n+++ b/" not in diff or "\n@@" not in diff:
        raise ValueError("patch must be a repository-relative unified diff")
    for line in diff.splitlines():
        if line.startswith(("--- ", "+++ ")) and (".." in line or line.startswith(("--- /", "+++ /"))):
            raise ValueError("patch contains an unsafe path")
    return diff


def _prompt(role: str, issue: str) -> str:
    return (PROMPTS / f"{role}.txt").read_text(encoding="utf-8").format(issue=issue)


def _ask(client: ChatClient, role: str, issue: str, schema: type[BaseModel]) -> BaseModel:
    return validated_response(schema, lambda prompt: client.chat(role, prompt).text, _prompt(role, issue))


async def run_agent(source: str, emit: Emit, options: dict | None = None) -> None:
    from app.agent.loop import run_agent_loop
    await run_agent_loop(source, emit, options)

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> object:
    cleaned = _THINK.sub("", text).strip()
    fenced = _FENCE.search(cleaned)
    if fenced:
        cleaned = fenced.group(1).strip()
    start = cleaned.find("{")
    if start < 0:
        raise ValueError("no JSON object found")
    decoder = json.JSONDecoder()
    value, _ = decoder.raw_decode(cleaned[start:])
    return value


def validated_response(model: type[T], ask: Callable[[str], str], prompt: str) -> T:
    """Ask at most three times, including the prior validation error on retries."""
    current = prompt
    last_error = "invalid output"
    for _ in range(3):
        try:
            return model.model_validate(extract_json(ask(current)))
        except (ValueError, ValidationError) as error:
            last_error = str(error)
            current = f"{prompt}\nYour previous output was invalid: {last_error}\nReturn only valid JSON matching the schema."
    raise ValueError(f"model response could not be validated after 3 attempts: {last_error}")


async def async_validated_response(
    model: type[T],
    ask: Callable[[str], Awaitable[Any]],
    prompt: str,
) -> T:
    """Ask at most three times asynchronously, including the prior validation error on retries."""
    current = prompt
    last_error = "invalid output"
    for _ in range(3):
        try:
            res = await ask(current)
            raw = res.text if hasattr(res, "text") else str(res)
            return model.model_validate(extract_json(raw))
        except (ValueError, ValidationError) as error:
            last_error = str(error)
            current = f"{prompt}\nYour previous output was invalid: {last_error}\nReturn only valid JSON matching the schema."
    raise ValueError(f"model response could not be validated after 3 attempts: {last_error}")

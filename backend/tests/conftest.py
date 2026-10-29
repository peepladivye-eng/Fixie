"""Pytest fixtures for hermetic backend test runs."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def hermetic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure tests are offline and hermetic by default."""
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    venv_scripts = str(Path(sys.executable).parent)
    monkeypatch.setenv("PATH", f"{venv_scripts}{os.pathsep}{os.environ.get('PATH', '')}")

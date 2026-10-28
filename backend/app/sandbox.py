from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

MAX_OUTPUT = 20_000
TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False


class LocalSandbox:
    """Fixture-only local execution, contained in a disposable temp directory."""
    def __init__(self, root: Path, workdir: Path) -> None:
        self.root, self.workdir = root.resolve(), workdir.resolve()

    @classmethod
    def open(cls, source: str) -> "LocalSandbox":
        if os.getenv("FIXIE_ALLOW_LOCAL") != "1":
            raise PermissionError("local sandbox requires FIXIE_ALLOW_LOCAL=1")
        if not source.startswith("fixture:"):
            raise ValueError("LocalSandbox only accepts fixture:<name> sources")
        name = source.removeprefix("fixture:")
        if not name or Path(name).name != name:
            raise ValueError("invalid fixture name")
        app_dir = Path(__file__).resolve().parent
        configured = os.getenv("FIXIE_FIXTURES_DIR")
        roots = [Path(configured)] if configured else [app_dir.parent / "eval" / "fixtures", app_dir.parent / "tests" / "core" / "fixtures"]
        fixture = next((root / name for root in roots if (root / name / "repo").is_dir()), None)
        if fixture is None:
            raise FileNotFoundError(f"fixture not found: {name}")
        root = Path(tempfile.mkdtemp(prefix="fixie-local-"))
        workdir = root / "repo"
        shutil.copytree(fixture / "repo", workdir)
        return cls(root, workdir)

    def _inside(self, path: Path) -> Path:
        resolved = path.resolve()
        if resolved != self.root and self.root not in resolved.parents:
            raise PermissionError("sandbox operation escaped temporary root")
        return resolved

    def checkpoint(self) -> Path:
        target = self._inside(self.root / "checkpoint")
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(self.workdir, target)
        return target

    def fork(self, count: int) -> list["LocalSandbox"]:
        if count < 1:
            raise ValueError("fork count must be positive")
        checkpoint = self.checkpoint()
        forks = []
        for index in range(count):
            target = self._inside(self.root / f"fork-{index + 1}")
            shutil.copytree(checkpoint, target)
            forks.append(LocalSandbox(self.root, target))
        return forks

    def run(self, command: str, timeout: int = TIMEOUT_SECONDS) -> CommandResult:
        try:
            done = subprocess.run(command, cwd=self._inside(self.workdir), shell=True, capture_output=True, text=True, timeout=timeout)
            return CommandResult(done.returncode, done.stdout[-MAX_OUTPUT:], done.stderr[-MAX_OUTPUT:])
        except subprocess.TimeoutExpired as error:
            return CommandResult(-1, (error.stdout or "")[-MAX_OUTPUT:], (error.stderr or "")[-MAX_OUTPUT:], True)

    def apply_diff(self, diff: str) -> CommandResult:
        if not diff.startswith("--- ") or "\n+++ " not in diff:
            return CommandResult(2, "", "invalid unified diff")
        patch_file = self._inside(self.root / "candidate.patch")
        patch_file.write_text(diff, encoding="utf-8")
        try:
            # `--no-index` works for copied fixtures that are not Git worktrees.
            done = subprocess.run(["git", "apply", "--no-index", "--ignore-space-change", "--whitespace=nowarn", str(patch_file)], cwd=self._inside(self.workdir), capture_output=True, text=True, timeout=TIMEOUT_SECONDS)
            return CommandResult(done.returncode, done.stdout[-MAX_OUTPUT:], done.stderr[-MAX_OUTPUT:])
        except FileNotFoundError:
            return CommandResult(127, "", "git executable is required to apply unified diffs")
        except subprocess.TimeoutExpired as error:
            return CommandResult(-1, (error.stdout or "")[-MAX_OUTPUT:], (error.stderr or "")[-MAX_OUTPUT:], True)
        finally:
            if patch_file.exists():
                patch_file.unlink()

    def close(self) -> None:
        if self.root.exists():
            shutil.rmtree(self._inside(self.root))

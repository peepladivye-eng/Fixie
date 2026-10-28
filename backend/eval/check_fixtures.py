"""Verify fixture bugs fail before, and pass after, their private reference patch.

LocalSandbox must copy only each repo/ directory; it must never expose solution.patch
or hidden_tests/ to the agent.
"""
import shutil, subprocess, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).parent / "fixtures"
def run(path, fixture, hidden=False):
    if hidden: shutil.copytree(fixture / "hidden_tests", path / "hidden_tests", dirs_exist_ok=True)
    return subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=path, capture_output=True, text=True).returncode
def main():
    valid = []
    for fixture in sorted(p for p in ROOT.iterdir() if p.is_dir()):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / "repo"; shutil.copytree(fixture / "repo", repo)
            before_visible, before_hidden = run(repo, fixture), run(repo, fixture, True)
            subprocess.run(["git", "apply", str(fixture / "solution.patch")], cwd=repo, check=True, capture_output=True)
            after_visible, after_hidden = run(repo, fixture), run(repo, fixture, True)
            if any((before_visible == 0, before_hidden == 0, after_visible != 0, after_hidden != 0)): raise SystemExit(f"invalid fixture: {fixture.name}")
            valid.append(fixture.name)
    print("fixtures valid: " + ", ".join(valid))
if __name__ == "__main__": main()

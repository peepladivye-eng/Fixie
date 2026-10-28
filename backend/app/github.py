from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path

import httpx

ISSUE_URL = re.compile(r"^https://github\.com/([^/]+)/([^/]+)/issues/(\d+)/?$")


def parse_issue_url(url: str) -> tuple[str, str, int]:
    match = ISSUE_URL.match(url)
    if not match:
        raise ValueError("expected https://github.com/<owner>/<repo>/issues/<n>")
    return match.group(1), match.group(2), int(match.group(3))


class GitHubClient:
    def __init__(self, token: str | None = None, client: httpx.Client | None = None) -> None:
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            raise RuntimeError("GITHUB_TOKEN is required for GitHub operations")
        self.client = client or httpx.Client(base_url="https://api.github.com", headers={"Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json"}, timeout=30.0)

    def issue(self, url: str) -> dict:
        owner, repo, number = parse_issue_url(url)
        # TODO(VERIFY): GitHub Get an issue endpoint contract.
        response = self.client.get(f"/repos/{owner}/{repo}/issues/{number}")
        response.raise_for_status()
        item = response.json()
        return {"owner": owner, "repo": repo, "number": number, "title": item["title"], "body": item.get("body") or ""}

    def download_repo(self, owner: str, repo: str, ref: str = "HEAD") -> Path:
        # TODO(VERIFY): GitHub zipball endpoint behavior.
        response = self.client.get(f"/repos/{owner}/{repo}/zipball/{ref}")
        response.raise_for_status()
        root = Path(tempfile.mkdtemp(prefix="fixie-github-"))
        with zipfile.ZipFile(BytesIO(response.content)) as archive:
            archive.extractall(root)
        children = list(root.iterdir())
        if len(children) != 1 or not children[0].is_dir():
            shutil.rmtree(root)
            raise ValueError("unexpected GitHub zipball layout")
        return children[0]

    def create_branch_commit_pr(self, owner: str, repo: str, base: str, branch: str, diff: str, title: str, body: str) -> str:
        """Apply a winner diff locally, then create Git objects and a pull request."""
        if not branch or branch.startswith("-"):
            raise ValueError("branch name is invalid")
        changed: dict[str, str | None] = {}
        old_path: str | None = None
        for line in diff.splitlines():
            if line.startswith("--- "):
                old_path = line[4:].removeprefix("a/")
            elif line.startswith("+++ "):
                new_path = line[4:]
                if new_path.startswith("b/"):
                    changed[new_path[2:]] = new_path[2:]
                elif new_path == "/dev/null" and old_path and old_path != "/dev/null":
                    changed[old_path] = None
        if not changed:
            raise ValueError("diff contains no changed repository files")
        checkout = self.download_repo(owner, repo, base)
        checkout_root = checkout.parent
        try:
            patch_file = checkout_root / "winner.patch"
            patch_file.write_text(diff, encoding="utf-8")
            applied = subprocess.run(["git", "apply", "--no-index", "--ignore-space-change", str(patch_file)], cwd=checkout, capture_output=True, text=True, timeout=60)
            if applied.returncode != 0:
                raise ValueError(f"winner diff did not apply cleanly: {applied.stderr[-2000:]}")
            # TODO(VERIFY): GitHub Get a reference endpoint contract.
            ref = self.client.get(f"/repos/{owner}/{repo}/git/ref/heads/{base}")
            ref.raise_for_status()
            parent_sha = ref.json()["object"]["sha"]
            # TODO(VERIFY): GitHub Create a reference endpoint contract.
            created = self.client.post(f"/repos/{owner}/{repo}/git/refs", json={"ref": f"refs/heads/{branch}", "sha": parent_sha})
            created.raise_for_status()
            # TODO(VERIFY): GitHub Get a commit endpoint contract.
            parent = self.client.get(f"/repos/{owner}/{repo}/git/commits/{parent_sha}")
            parent.raise_for_status()
            tree_entries = []
            for path, current_path in changed.items():
                if current_path is None:
                    tree_entries.append({"path": path, "mode": "100644", "type": "blob", "sha": None})
                    continue
                content = (checkout / current_path).read_bytes()
                # TODO(VERIFY): GitHub Create a blob endpoint contract.
                blob = self.client.post(f"/repos/{owner}/{repo}/git/blobs", json={"content": content.decode("utf-8"), "encoding": "utf-8"})
                blob.raise_for_status()
                tree_entries.append({"path": current_path, "mode": "100644", "type": "blob", "sha": blob.json()["sha"]})
            # TODO(VERIFY): GitHub Create a tree endpoint contract.
            tree = self.client.post(f"/repos/{owner}/{repo}/git/trees", json={"base_tree": parent.json()["tree"]["sha"], "tree": tree_entries})
            tree.raise_for_status()
            # TODO(VERIFY): GitHub Create a commit endpoint contract.
            commit = self.client.post(f"/repos/{owner}/{repo}/git/commits", json={"message": title, "tree": tree.json()["sha"], "parents": [parent_sha]})
            commit.raise_for_status()
            # TODO(VERIFY): GitHub Update a reference endpoint contract.
            updated = self.client.patch(f"/repos/{owner}/{repo}/git/refs/heads/{branch}", json={"sha": commit.json()["sha"], "force": False})
            updated.raise_for_status()
            # TODO(VERIFY): GitHub Create a pull request endpoint contract.
            pull = self.client.post(f"/repos/{owner}/{repo}/pulls", json={"title": title, "head": branch, "base": base, "body": body})
            pull.raise_for_status()
            return str(pull.json()["html_url"])
        finally:
            shutil.rmtree(checkout_root, ignore_errors=True)

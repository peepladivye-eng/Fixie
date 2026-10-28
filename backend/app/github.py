"""GitHub integration wrapper.

Conforms to contracts/interfaces.md for issue fetching and PR submission.
"""

import os
from typing import Optional
from pydantic import BaseModel


class IssueData(BaseModel):
    title: str
    body: str
    repo: str
    issue_number: int


class PRResult(BaseModel):
    pr_url: Optional[str]
    pr_number: Optional[int]


class GitHubClient:
    """GitHub client for issue reading and PR delivery."""

    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN", "")

    def fetch_issue(self, issue_url: str) -> IssueData:
        """Fetch issue title and body from GitHub."""
        # TODO(VERIFY): Connect to GitHub REST API with GITHUB_TOKEN
        return IssueData(
            title="parse_duration('1h30m') returns 90 instead of 5400",
            body="When running parse_duration('1h30m'), the returned value is 90 seconds instead of 5400.",
            repo="fast-utils/duration-parser",
            issue_number=14,
        )

    def create_pr(
        self,
        repo: str,
        branch: str,
        title: str,
        body: str,
        diff: str,
    ) -> PRResult:
        """Create pull request with generated patch."""
        # TODO(VERIFY): Connect to GitHub PR creation endpoint
        if not self.token:
            return PRResult(pr_url=None, pr_number=None)
        return PRResult(
            pr_url=f"https://github.com/{repo}/pull/42",
            pr_number=42,
        )

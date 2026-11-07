"""GitHub REST helpers. Raw requests; PyGithub joins when repo creation and secrets need it."""

from __future__ import annotations

import os

import requests

API = "https://api.github.com"
TIMEOUT = 30


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def get(path: str, token: str) -> requests.Response:
    """GET an API path with the given token."""
    return requests.get(API + path, headers=_headers(token), timeout=TIMEOUT)


def post_comment(repo: str, issue_number: int, body: str, token: str | None = None) -> None:
    """Comment on an issue or PR with GITHUB_TOKEN.

    The orchestrator's own comments never start with '/', so they cannot trigger a command.
    """
    if body.lstrip().startswith("/"):
        raise ValueError("orchestrator comments must not start with '/'")
    token = token or os.environ.get("GITHUB_TOKEN", "").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN is not set")
    resp = requests.post(
        f"{API}/repos/{repo}/issues/{issue_number}/comments",
        headers=_headers(token),
        json={"body": body},
        timeout=TIMEOUT,
    )
    resp.raise_for_status()

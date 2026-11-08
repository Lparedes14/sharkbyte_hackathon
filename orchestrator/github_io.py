"""GitHub REST helpers. Raw requests; PyGithub joins when repo creation and secrets need it.

Comments, labels and doc files in the current repo use GITHUB_TOKEN. Events created with
GITHUB_TOKEN do not start new workflow runs, so the orchestrator cannot loop on itself.
"""

from __future__ import annotations

import base64
import os
from urllib.parse import quote

import requests

API = "https://api.github.com"
TIMEOUT = 30


class GitHubError(Exception):
    """A GitHub API call failed. The message names the call, never a token."""


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _token(token: str | None) -> str:
    value = (token or os.environ.get("GITHUB_TOKEN", "")).strip()
    if not value:
        raise GitHubError("GITHUB_TOKEN is not set")
    return value


def _request(method: str, path: str, token: str | None = None, ok: tuple = (200, 201), **kwargs):
    resp = requests.request(
        method, API + path, headers=_headers(_token(token)), timeout=TIMEOUT, **kwargs
    )
    if resp.status_code not in ok:
        raise GitHubError(f"{method} {path.split('?')[0]} returned HTTP {resp.status_code}")
    return resp


def get(path: str, token: str) -> requests.Response:
    """GET an API path with the given token (used by the health check)."""
    return requests.get(API + path, headers=_headers(token), timeout=TIMEOUT)


def post_comment(repo: str, issue_number: int, body: str, token: str | None = None) -> None:
    """Comment on an issue or PR. The orchestrator's own comments never start with '/'."""
    if body.lstrip().startswith("/"):
        raise ValueError("orchestrator comments must not start with '/'")
    _request("POST", f"/repos/{repo}/issues/{issue_number}/comments", token, ok=(201,), json={"body": body})


def get_issue(repo: str, issue_number: int, token: str | None = None) -> dict:
    return _request("GET", f"/repos/{repo}/issues/{issue_number}", token, ok=(200,)).json()


def list_comments(repo: str, issue_number: int, token: str | None = None) -> list[dict]:
    resp = _request(
        "GET", f"/repos/{repo}/issues/{issue_number}/comments?per_page=100", token, ok=(200,)
    )
    return resp.json()


def ensure_label(repo: str, name: str, color: str, description: str, token: str | None = None) -> None:
    """Create the label if it does not exist yet (422 means it already exists)."""
    _request(
        "POST",
        f"/repos/{repo}/labels",
        token,
        ok=(201, 422),
        json={"name": name, "color": color, "description": description},
    )


def add_labels(repo: str, issue_number: int, labels: list[str], token: str | None = None) -> None:
    _request(
        "POST", f"/repos/{repo}/issues/{issue_number}/labels", token, ok=(200,), json={"labels": labels}
    )


def remove_label(repo: str, issue_number: int, label: str, token: str | None = None) -> None:
    _request(
        "DELETE",
        f"/repos/{repo}/issues/{issue_number}/labels/{quote(label, safe='')}",
        token,
        ok=(200, 404),
    )


def get_file(repo: str, path: str, ref: str, token: str | None = None) -> tuple[str | None, str | None]:
    """(text, sha) of a file on a branch, or (None, None) when it does not exist."""
    resp = _request(
        "GET", f"/repos/{repo}/contents/{quote(path)}?ref={quote(ref, safe='')}", token, ok=(200, 404)
    )
    if resp.status_code == 404:
        return None, None
    data = resp.json()
    text = base64.b64decode(data.get("content", "")).decode("utf-8")
    return text, data.get("sha")


def put_file(repo: str, path: str, text: str, message: str, branch: str, token: str | None = None) -> None:
    """Create or update one file with a commit on the branch."""
    _, sha = get_file(repo, path, branch, token)
    body = {
        "message": message,
        "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
        "branch": branch,
    }
    if sha:
        body["sha"] = sha
    _request("PUT", f"/repos/{repo}/contents/{quote(path)}", token, ok=(200, 201), json=body)

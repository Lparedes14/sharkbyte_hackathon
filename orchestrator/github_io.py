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


def create_repo(name: str, private: bool, description: str, token: str) -> dict:
    """Create a repo for the token's user, with a README so it has a default branch."""
    resp = requests.post(
        API + "/user/repos",
        headers=_headers(token),
        timeout=TIMEOUT,
        json={"name": name, "private": private, "auto_init": True, "description": description[:350]},
    )
    if resp.status_code == 422:
        raise GitHubError(f"a repository named '{name}' already exists or the name is not allowed")
    if resp.status_code in (401, 403, 404):
        raise GitHubError(
            f"GH_TOKEN cannot create repositories (HTTP {resp.status_code}); it needs "
            "All repositories access and Administration: Read and write"
        )
    if resp.status_code != 201:
        raise GitHubError(f"POST /user/repos returned HTTP {resp.status_code}")
    return resp.json()


def branch_exists(repo: str, branch: str, token: str | None = None) -> bool:
    resp = _request("GET", f"/repos/{repo}/branches/{quote(branch, safe='')}", token, ok=(200, 404))
    return resp.status_code == 200


def create_issue(repo: str, title: str, body: str, token: str | None = None) -> dict:
    return _request(
        "POST", f"/repos/{repo}/issues", token, ok=(201,), json={"title": title, "body": body}
    ).json()


# Commands the orchestrator may post on purpose, with GH_TOKEN, to start a workflow in another
# repo (events made with GITHUB_TOKEN never start workflows). Nothing else may start with '/'.
ALLOWED_COMMANDS = ("/run discovery",)


def post_command(repo: str, issue_number: int, command: str, token: str) -> None:
    if command not in ALLOWED_COMMANDS:
        raise ValueError(f"the orchestrator may not post '{command}'")
    _request("POST", f"/repos/{repo}/issues/{issue_number}/comments", token, ok=(201,), json={"body": command})


def secrets_public_key(repo: str, token: str) -> dict:
    return _request("GET", f"/repos/{repo}/actions/secrets/public-key", token, ok=(200,)).json()


def put_secret(repo: str, name: str, encrypted_value: str, key_id: str, token: str) -> None:
    _request(
        "PUT",
        f"/repos/{repo}/actions/secrets/{quote(name, safe='')}",
        token,
        ok=(201, 204),
        json={"encrypted_value": encrypted_value, "key_id": key_id},
    )


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


def list_dir(repo: str, path: str, ref: str, token: str | None = None) -> list[str]:
    """File paths directly inside a folder on a branch; empty when the folder does not exist."""
    resp = _request(
        "GET", f"/repos/{repo}/contents/{quote(path)}?ref={quote(ref, safe='')}", token, ok=(200, 404)
    )
    if resp.status_code == 404:
        return []
    data = resp.json()
    return [item["path"] for item in data if isinstance(item, dict) and item.get("type") == "file"]


def delete_file(repo: str, path: str, message: str, branch: str, token: str | None = None) -> None:
    """Delete one file with a commit on the branch (nothing happens when it does not exist)."""
    _, sha = get_file(repo, path, branch, token)
    if not sha:
        return
    body = {"message": message, "sha": sha, "branch": branch}
    _request("DELETE", f"/repos/{repo}/contents/{quote(path)}", token, ok=(200,), json=body)

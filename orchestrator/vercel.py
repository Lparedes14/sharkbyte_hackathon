"""Vercel REST API: give each project repo its own Vercel project with public previews.

One VERCEL_TOKEN (home base secret only) covers every project on the account. For each new
repo, /build creates (or reuses) a Vercel project linked to it and turns off Vercel
Authentication ("Require Log In"), so QA Tester can open the previews.

Hobby accounts live under a personal team; the team comes from VERCEL_TEAM_ID or, when that
is not set, from the user's defaultTeamId. The token is never printed or logged.
"""

from __future__ import annotations

import os

import requests

API = "https://api.vercel.com"
FRAMEWORK = "nextjs"
# A new repo only has docs until Cursor scaffolds the app, and a Next.js build of that fails. Vercel skips a
# build when this command exits 0, and builds when it exits 1, so builds start once package.json exists.
SKIP_UNTIL_APP = "test ! -f package.json"
TIMEOUT = 30


class VercelError(Exception):
    """A Vercel call failed. The message is safe to post and says what to fix."""


def token() -> str:
    return os.environ.get("VERCEL_TOKEN", "").strip()


def _headers() -> dict:
    return {"Authorization": f"Bearer {token()}", "Content-Type": "application/json"}


def _error(resp: requests.Response, action: str) -> VercelError:
    try:
        message = (resp.json().get("error") or {}).get("message", "")
    except ValueError:
        message = ""
    return VercelError(f"{action} returned HTTP {resp.status_code}" + (f": {message}" if message else ""))


def _user() -> dict:
    if not token():
        raise VercelError("VERCEL_TOKEN is not set")
    try:
        resp = requests.get(API + "/v2/user", headers=_headers(), timeout=TIMEOUT)
    except requests.RequestException as exc:
        raise VercelError(f"request failed ({type(exc).__name__})") from None
    if resp.status_code != 200:
        raise _error(resp, "the token check")
    return resp.json().get("user") or {}


def _team_params() -> dict:
    team = os.environ.get("VERCEL_TEAM_ID", "").strip() or _user().get("defaultTeamId") or ""
    return {"teamId": team} if team else {}


def check() -> tuple[bool, str]:
    """For /ping: does the token work, and which account does it act for?"""
    try:
        user = _user()
    except VercelError as exc:
        return False, str(exc)
    team = os.environ.get("VERCEL_TEAM_ID", "").strip() or user.get("defaultTeamId")
    return True, f"signed in as {user.get('username', '?')}" + ("; team found" if team else "")


def project_name(repo_full: str) -> str:
    """The Vercel project gets the repo's name (lowercase)."""
    return repo_full.split("/")[-1].lower()


def production_url(name: str) -> str | None:
    """The project's stable production domain (name.vercel.app), known before the first deploy."""
    try:
        resp = requests.get(
            f"{API}/v9/projects/{name}/domains", headers=_headers(), params=_team_params(), timeout=TIMEOUT
        )
        if resp.status_code != 200:
            return None
        for domain in resp.json().get("domains", []):
            host = domain.get("name", "")
            if host.endswith(".vercel.app") and not domain.get("redirect") and not domain.get("gitBranch"):
                return "https://" + host
    except (requests.RequestException, ValueError, VercelError):
        return None
    return None


def link_repo(repo_full: str) -> str:
    """Create or reuse the Vercel project for this repo, then make its previews public.

    Returns the Vercel project name.
    """
    params = _team_params()
    name = project_name(repo_full)
    try:
        resp = requests.get(f"{API}/v9/projects/{name}", headers=_headers(), params=params, timeout=TIMEOUT)
        if resp.status_code == 404:
            resp = requests.post(
                f"{API}/v11/projects",
                headers=_headers(),
                params=params,
                timeout=TIMEOUT,
                # The default stack is Next.js. Without this the project is "Other" (static) and the
                # first build fails with "No Output Directory named public" once the app exists.
                json={
                    "name": name,
                    "framework": FRAMEWORK,
                    "commandForIgnoringBuildStep": SKIP_UNTIL_APP,
                    "gitRepository": {"type": "github", "repo": repo_full},
                },
            )
            if resp.status_code not in (200, 201):
                error = _error(resp, "creating the Vercel project")
                if resp.status_code in (400, 403, 404) and "repo" in str(error).lower():
                    raise VercelError(
                        f"{error}. Vercel cannot see the repo: in GitHub settings, give the Vercel "
                        "app access to All repositories"
                    )
                raise error
        elif resp.status_code != 200:
            raise _error(resp, "reading the Vercel project")
        project = resp.json()

        settings: dict = {"ssoProtection": None}
        if not project.get("framework"):
            settings["framework"] = FRAMEWORK  # only fills in an unset preset, never overrides one

        resp = requests.patch(
            f"{API}/v9/projects/{project.get('id', name)}",
            headers=_headers(),
            params=params,
            timeout=TIMEOUT,
            json=settings,
        )
        if resp.status_code != 200:
            raise _error(resp, "turning off Require Log In and setting the framework")
    except requests.RequestException as exc:
        raise VercelError(f"request failed ({type(exc).__name__})") from None
    return name

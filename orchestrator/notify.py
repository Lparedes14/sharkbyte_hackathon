"""Calls the Grok Bot webhooks (PLAN.md section 7).

Each bot has a URL and a key, stored as <PREFIX>_WEBHOOK and <PREFIX>_WEBHOOK_KEY.
The key is sent as "Authorization: Bearer <key>" (S2). An optional <PREFIX>_WEBHOOK_HEADER
overrides the header name. URLs and keys are never printed or logged.
"""

from __future__ import annotations

import os

import requests

TIMEOUT = 30

# env prefix -> label
BOTS = {
    "PROJECT_LEAD": "Project Lead",
    "PROGRESS_REPORTER": "Progress Reporter",
    "QA_TESTER": "QA Tester",
}


def missing_settings(prefix: str) -> list[str]:
    """Names of the required env vars that are empty for this bot."""
    names = (f"{prefix}_WEBHOOK", f"{prefix}_WEBHOOK_KEY")
    return [n for n in names if not os.environ.get(n, "").strip()]


def make_payload(
    event: str,
    repo: str,
    link: str,
    summary: str,
    question: str = "",
    preview_url: str | None = None,
) -> dict:
    """Webhook body in our own format (PLAN.md section 7)."""
    return {
        "event": event,
        "repo": f"https://github.com/{repo}" if repo else "",
        "link": link,
        "summary": summary,
        "question": question,
        "preview_url": preview_url,
    }


def send(prefix: str, payload: dict) -> tuple[bool, str]:
    """POST the payload to one bot. Returns (ok, short detail that is safe to publish)."""
    if missing_settings(prefix):
        return False, "webhook URL or key is not set"

    url = os.environ[f"{prefix}_WEBHOOK"].strip()
    key = os.environ[f"{prefix}_WEBHOOK_KEY"].strip()
    header = os.environ.get(f"{prefix}_WEBHOOK_HEADER", "").strip() or "Authorization"
    if header.lower() == "authorization" and not key.lower().startswith("bearer "):
        key = "Bearer " + key

    try:
        resp = requests.post(
            url,
            headers={header: key, "Content-Type": "application/json"},
            json=payload,
            timeout=TIMEOUT,
        )
    except requests.RequestException as exc:
        # The exception text can contain the URL, so report only its class name.
        return False, f"request failed ({type(exc).__name__})"

    if not 200 <= resp.status_code < 300:
        return False, f"HTTP {resp.status_code}"
    try:
        data = resp.json()
    except ValueError:
        data = {}
    if isinstance(data, dict) and data.get("success") is False:
        return False, "webhook answered success=false"
    return True, f"HTTP {resp.status_code}"

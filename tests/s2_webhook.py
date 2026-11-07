"""S2: POST Project Lead Grok Bot webhook with PLAN.md section 7 payload."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "PROJECT_LEAD_WEBHOOK",
    "PROJECT_LEAD_WEBHOOK_KEY",
    "PROJECT_LEAD_WEBHOOK_HEADER",
)

BODY = {
    "event": "ping",
    "repo": "https://github.com/Lparedes14/sharkbyte_hackathon",
    "link": "https://github.com/Lparedes14/sharkbyte_hackathon",
    "summary": "S2 webhook test",
    "question": "Did you get this message?",
    "preview_url": None,
}


def main() -> None:
    load_dotenv(ROOT / ".env")

    missing = [name for name in REQUIRED if not (os.getenv(name) or "").strip()]
    if missing:
        print("Missing or empty env var(s): " + ", ".join(missing))
        sys.exit(1)

    url = os.getenv("PROJECT_LEAD_WEBHOOK", "").strip()
    key = os.getenv("PROJECT_LEAD_WEBHOOK_KEY", "").strip()
    header_name = os.getenv("PROJECT_LEAD_WEBHOOK_HEADER", "").strip()

    headers = {
        header_name: key,
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, headers=headers, json=BODY, timeout=30)
    except requests.RequestException as exc:
        # Avoid printing URL or headers; keep the error class/message only.
        print(f"Request failed: {type(exc).__name__}")
        sys.exit(1)

    body = resp.text or ""
    if not (200 <= resp.status_code < 300):
        print(f"HTTP {resp.status_code}")
        print(body)
        sys.exit(1)

    preview = body[:300]
    print(f"HTTP {resp.status_code}")
    print(preview)


if __name__ == "__main__":
    main()

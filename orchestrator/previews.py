"""Where the app can be seen: the preview URL of a PR and the production URL of the project.

Vercel creates no GitHub Deployments (S6), so it reports through two things this module reads:
- the `vercel[bot]` comment on the PR carries a hidden base64 JSON block with `previewUrl`
- the production URL is the project's stable domain, written to docs/LINKS.md by /build
"""

from __future__ import annotations

import base64
import json
import re

VC_BLOCK = re.compile(r"\[vc\]:\s*#[^:\s]*:([A-Za-z0-9+/=_-]+)")
PREVIEW_LINK = re.compile(r"\[Preview\]\((https://[^)\s]+)\)")
PRODUCTION_LINE = re.compile(r"Production:\s*(https?://\S+)", re.IGNORECASE)


def _https(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    return url if url.startswith("http") else "https://" + url


def preview_url_from_body(body: str) -> str | None:
    """The preview URL inside one Vercel bot comment, or None while it has none yet."""
    match = VC_BLOCK.search(body or "")
    if match:
        raw = match.group(1)
        try:
            data = json.loads(base64.b64decode(raw + "=" * (-len(raw) % 4), altchars=b"-_").decode("utf-8"))
            for project in data.get("projects") or []:
                url = _https(project.get("previewUrl", ""))
                if url:
                    return url
        except (ValueError, UnicodeDecodeError):
            pass
    link = PREVIEW_LINK.search(body or "")
    return link.group(1) if link else None


def preview_url_from_comments(comments: list[dict]) -> str | None:
    """The newest preview URL among the Vercel bot's comments on a PR."""
    for comment in reversed(comments or []):
        login = (comment.get("user") or {}).get("login", "")
        if not login.lower().startswith("vercel"):
            continue
        url = preview_url_from_body(comment.get("body", ""))
        if url:
            return url
    return None


def production_url_from_links(text: str | None) -> str | None:
    match = PRODUCTION_LINE.search(text or "")
    return match.group(1).rstrip(".,)") if match else None


NON_UI_PREFIXES = ("supabase/", "docs/", "tasks/", ".github/", ".cursor/", "scripts/", "tests/", "test/", "__tests__/")
NON_UI_SUFFIXES = (".sql", ".md", ".txt", ".yml", ".yaml", ".json", ".lock", ".gitignore", ".env.example")


def is_ui_change(files: list[str]) -> bool:
    """False when a PR only touches SQL, docs, config or tests: nothing a browser can check.

    Lock files and package.json alone do not change what the user sees either.
    """
    for path in files:
        if path.startswith(NON_UI_PREFIXES) or path.endswith(NON_UI_SUFFIXES):
            continue
        return True
    return False


def links_doc(production_url: str) -> str:
    return (
        "# Links\n\n"
        "Written by `/build`. Progress Reporter and the orchestrator read the production URL from here.\n\n"
        f"Production: {production_url}\n"
    )

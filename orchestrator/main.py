"""Orchestrator entry point (PLAN.md section 7).

Run by GitHub Actions on an issue comment. It reads the event file (user text never goes
through shell interpolation), accepts only commands from the repo owner, and routes them.

Local check without posting or calling the bots:  python orchestrator/main.py --local
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

import github_io
import health

ROOT = Path(__file__).resolve().parents[1]


def parse_command(body: str) -> str:
    """Return the lowercase command word, like '/ping', or '' when the comment has none."""
    text = (body or "").strip()
    if not text:
        return ""
    first_word = text.splitlines()[0].split(maxsplit=1)[0]
    return first_word.lower() if first_word.startswith("/") else ""


def handle_ping(repo: str, issue_number: int) -> None:
    link = f"https://github.com/{repo}/issues/{issue_number}"
    results = health.run_all(repo=repo, link=link, send_webhooks=True)
    github_io.post_comment(repo, issue_number, health.format_comment(results, repo))
    for r in results:
        print(f"{'ok' if r.ok else 'FAILED'}: {r.name} - {r.detail}")


COMMANDS = {"/ping": handle_ping}


def run_event() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    event_path = os.environ.get("GITHUB_EVENT_PATH", "")
    if event_name != "issue_comment" or not event_path:
        print("Not a comment event; nothing to do.")
        return 0

    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    if event.get("action") != "created":
        print("Comment was not newly created; nothing to do.")
        return 0

    repository = event.get("repository") or {}
    repo = repository.get("full_name", "")
    owner = (repository.get("owner") or {}).get("login", "")
    author = ((event.get("comment") or {}).get("user") or {}).get("login", "")
    issue_number = (event.get("issue") or {}).get("number")

    # Defense in depth: the workflow already checks this.
    if not owner or author != owner:
        print("Ignored: the comment is not from the repo owner.")
        return 0

    command = parse_command((event.get("comment") or {}).get("body", ""))
    if not command:
        print("Ignored: the comment is not a command.")
        return 0

    os.environ["GITHUB_REPOSITORY"] = repo
    handler = COMMANDS.get(command)
    if handler is None:
        print("Ignored: unknown or not-yet-implemented command.")
        github_io.post_comment(
            repo,
            issue_number,
            "That command is not implemented yet. Available now: `/ping`.",
        )
        return 0

    handler(repo, issue_number)
    return 0


def run_local() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    results = health.run_all(repo=repo, link="(local run)", send_webhooks=False)
    print(health.format_comment(results, repo or "(GITHUB_REPOSITORY not set)"))
    return 0


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(ROOT / ".env")
    if "--local" in argv:
        return run_local()
    return run_event()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

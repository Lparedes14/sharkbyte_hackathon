"""Send a test "ping" to your Grok Bot webhooks and say whether each one answered.

Usage (from the repo root, with your values in .env):
  python tests/webhook_test.py all
  python tests/webhook_test.py project_lead
  python tests/webhook_test.py progress_reporter qa_tester

What it does: it sends the same message the orchestrator sends (event "ping") to the webhook URL of each
bot you name, with the key from .env. It prints one line per bot: ok or the problem, never the URL or the
key. After "ok", look in the Grok Bot app: the bot should message you "Webhook works".
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "orchestrator"))

import notify  # noqa: E402

BOTS = {
    "project_lead": "PROJECT_LEAD",
    "progress_reporter": "PROGRESS_REPORTER",
    "qa_tester": "QA_TESTER",
}
HELP = {
    "HTTP 401": "the key is wrong or has the wrong header: check <BOT>_WEBHOOK_KEY (and <BOT>_WEBHOOK_HEADER, normally Authorization)",
    "HTTP 404": "the webhook URL is wrong or the routine was deleted: ask the bot for its webhook again",
    "not set": "fill in <BOT>_WEBHOOK and <BOT>_WEBHOOK_KEY in .env (see .env.example)",
}


def hint(detail: str) -> str:
    for key, text in HELP.items():
        if key in detail:
            return " -> " + text
    return ""


def main(argv: list[str]) -> int:
    load_dotenv(ROOT / ".env")
    names = list(BOTS) if not argv or argv == ["all"] else argv
    unknown = [n for n in names if n not in BOTS]
    if unknown:
        print(f"Unknown bot: {', '.join(unknown)}. Use: all, {', '.join(BOTS)}.")
        return 2

    failed = 0
    for name in names:
        prefix = BOTS[name]
        payload = notify.make_payload(
            "ping", "", "https://github.com", f"Webhook test for {name.replace('_', ' ')}.", "Did you get this message?"
        )
        ok, detail = notify.send(prefix, payload)
        print(f"{'ok   ' if ok else 'FAIL '}{name}: {detail}{'' if ok else hint(detail)}")
        failed += 0 if ok else 1
    if not failed:
        print("\nAll webhooks answered. Now check the Grok Bot app: each bot should have messaged you.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

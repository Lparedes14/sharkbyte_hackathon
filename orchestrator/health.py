"""The /ping health check (PLAN.md section 5): Swarms key, GitHub token, three bot webhooks."""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

import github_io
import notify
import swarms_client

PLAN_STEPS = "PLAN.md section 5"


@dataclass
class Result:
    name: str
    ok: bool
    detail: str
    fix: str = ""


def _ping_spec() -> dict:
    """Two tiny agents, the same shape as the S1 request that worked."""
    model = swarms_client.default_model()
    return {
        "name": "ping",
        "swarm_type": "SequentialWorkflow",
        "agents": [
            {
                "agent_name": "Greeter",
                "description": "Says hello briefly",
                "system_prompt": "You are Greeter. Reply in one short sentence.",
                "model_name": model,
                "max_loops": 1,
            },
            {
                "agent_name": "Responder",
                "description": "Acknowledges the greeter",
                "system_prompt": "You are Responder. Reply in one short sentence.",
                "model_name": model,
                "max_loops": 1,
            },
        ],
    }


def check_swarms() -> Result:
    try:
        swarms_client.run_swarm(
            _ping_spec(), "Each agent should say hello in one short sentence.", timeout=120
        )
    except swarms_client.SwarmsError as exc:
        return Result("Swarms key", False, str(exc), f"{PLAN_STEPS}, step 5")
    return Result("Swarms key", True, "tiny 2-agent call returned HTTP 200")


def check_github() -> Result:
    fix = f"{PLAN_STEPS}, steps 4 and 5"
    token = os.environ.get("GH_TOKEN", "").strip()
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if not token:
        return Result("GitHub token", False, "GH_TOKEN is not set", fix)
    if not repo:
        return Result("GitHub token", False, "GITHUB_REPOSITORY is not set", fix)

    try:
        resp = github_io.get("/user", token)
        if resp.status_code != 200:
            return Result("GitHub token", False, f"token rejected (HTTP {resp.status_code})", fix)
        login = resp.json().get("login", "?")

        resp = github_io.get(f"/repos/{repo}", token)
        if resp.status_code != 200:
            return Result("GitHub token", False, f"cannot read {repo} (HTTP {resp.status_code})", fix)

        resp = github_io.get(f"/repos/{repo}/actions/secrets/public-key", token)
        if resp.status_code != 200:
            return Result(
                "GitHub token",
                False,
                f"Secrets permission missing (HTTP {resp.status_code})",
                fix,
            )
    except requests.RequestException as exc:
        return Result("GitHub token", False, f"request failed ({type(exc).__name__})", fix)

    return Result("GitHub token", True, f"signed in as {login}; can read the repo; Secrets permission works")


def check_webhook(prefix: str, payload: dict | None) -> Result:
    """Send the payload (or only check the settings when payload is None)."""
    label = notify.BOTS[prefix]
    name = f"{label} webhook"
    fix = f"{PLAN_STEPS}, steps 3 and 5"

    missing = notify.missing_settings(prefix)
    if missing:
        return Result(name, False, "not set: " + ", ".join(missing), fix)
    if payload is None:
        return Result(name, True, "settings present (not sent in a local run)")

    ok, detail = notify.send(prefix, payload)
    return Result(name, ok, detail, "" if ok else fix)


def run_all(repo: str, link: str, send_webhooks: bool) -> list[Result]:
    """Run every check. Project Lead is called last, with the overall verdict as its message."""
    results = [
        Result("Workflow", True, "the orchestrator started"),
        check_swarms(),
        check_github(),
    ]

    def payload(summary: str, question: str = "") -> dict | None:
        if not send_webhooks:
            return None
        return notify.make_payload("ping", repo, link, summary, question)

    reporter = check_webhook(
        "PROGRESS_REPORTER", payload("Health check: Progress Reporter webhook works")
    )
    qa = check_webhook("QA_TESTER", payload("Health check: QA Tester webhook works"))

    before_lead = results + [reporter, qa]
    failed = [r.name for r in before_lead if not r.ok]
    if failed:
        summary = "Setup incomplete ❌. Still failing: " + ", ".join(failed)
    else:
        summary = "Setup complete ✅"
    lead = check_webhook(
        "PROJECT_LEAD", payload(summary, "Health check finished. Reply only if you want to change something.")
    )

    return results + [lead, reporter, qa]


def format_comment(results: list[Result], repo: str) -> str:
    """Markdown report. It starts with text, never with '/'."""
    lines = [
        f"Health check for {repo}",
        "",
        "| Check | Result | Details | Fix |",
        "|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r.name} | {'✅' if r.ok else '❌'} | {r.detail} | {r.fix or '-'} |")
    lines.append("")
    if all(r.ok for r in results):
        lines.append("**Setup complete ✅**")
    else:
        lines.append("**Setup incomplete ❌.** Fix the failing checks, then comment `/ping` again.")
    return "\n".join(lines)

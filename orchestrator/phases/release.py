"""Release (/release): a SequentialWorkflow decides the merge, the deploy checklist and the changelog.

PR & Merge Manager -> DevOps/Release -> Docs & Pitch Writer. The orchestrator then merges with
GH_TOKEN and writes the CHANGELOG entry. This only runs after the founder's own Go in chat.
"""

from __future__ import annotations

import datetime

from phases.common import PhaseError, as_list, call, json_from

REQUIRED = ("merge", "changelog")
SCHEMA = """{
  "merge": {"go": true, "method": "squash, merge or rebase", "reason": "one sentence"},
  "deploy_checklist": ["what to check on the live site after the deploy"],
  "env_vars": ["VARIABLE_NAME (names only, never values)"],
  "rollback": "one line",
  "changelog": ["short bullet in plain words: what a user can now do"],
  "release_note": "one line"
}"""
METHODS = ("squash", "merge", "rebase")


def run(facts: str) -> dict:
    """The normalized release plan for the facts text (vote, review, QA, PR state)."""
    task = (
        "Plan the release of this pull request. The PR & Merge Manager decides, DevOps/Release adds the "
        "deploy checklist, and the Docs & Pitch Writer gives the final answer, ending with one fenced "
        "json block that matches this schema:\n" + SCHEMA + "\n\nFACTS:\n" + facts[:8000]
    )
    response = call("release", task, "release")
    obj = json_from(
        response, REQUIRED, SCHEMA, roles=["Docs & Pitch Writer"], any_role_fallback=True, label="formatter-release"
    )
    merge = obj.get("merge") if isinstance(obj.get("merge"), dict) else {}
    method = str(merge.get("method", "squash")).strip().lower()
    return {
        "go": bool(merge.get("go", False)),
        "method": method if method in METHODS else "squash",
        "reason": str(merge.get("reason", "")).strip(),
        "checklist": as_list(obj.get("deploy_checklist")),
        "env_vars": as_list(obj.get("env_vars")),
        "rollback": str(obj.get("rollback", "")).strip(),
        "changelog": as_list(obj.get("changelog")) or ["Release of this change."],
        "note": str(obj.get("release_note", "")).strip(),
    }


def changelog_entry(pr_number: int, title: str, bullets: list[str], today: datetime.date | None = None) -> str:
    day = (today or datetime.date.today()).isoformat()
    lines = [f"## {day}: {title} (#{pr_number})", ""] + [f"- {b}" for b in bullets]
    return "\n".join(lines) + "\n"


def add_to_changelog(existing: str | None, entry: str) -> str:
    """Put the newest entry first, under the '# Changelog' heading."""
    if not existing or not existing.strip():
        return "# Changelog\n\n" + entry
    head, sep, rest = existing.partition("\n")
    if head.lstrip().startswith("# "):
        return head + "\n\n" + entry + "\n" + rest.lstrip("\n")
    return "# Changelog\n\n" + entry + "\n" + existing


def render_comment(plan: dict, merge_sha: str | None, override: bool) -> str:
    lines = [
        "**Released with `/release`** (Swarms `SequentialWorkflow`: PR & Merge Manager, then DevOps/Release, "
        "then Docs & Pitch Writer).",
        "",
        f"- Merge method: **{plan['method']}**" + (" (the hold vote was overridden)" if override else ""),
    ]
    if merge_sha:
        lines.append(f"- Merge commit: `{merge_sha[:8]}`")
    if plan["reason"]:
        lines.append(f"- Why: {plan['reason']}")
    if plan["note"]:
        lines.append(f"- Release note: {plan['note']}")
    if plan["checklist"]:
        lines += ["", "**Deploy checklist**"] + [f"- [ ] {c}" for c in plan["checklist"]]
    if plan["env_vars"]:
        lines += ["", "**Environment variables (names only)**"] + [f"- `{v}`" for v in plan["env_vars"]]
    if plan["rollback"]:
        lines += ["", f"**Rollback:** {plan['rollback']}"]
    lines += ["", "The CHANGELOG is updated on main. Vercel deploys production now."]
    return "\n".join(lines)

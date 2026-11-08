"""Code Review: a ConcurrentWorkflow of two independent reviewers reads a task PR's diff.

The Code Reviewer and the Security Reviewer each end with JSON. The orchestrator merges the
issues; only a high-severity issue means "changes". Medium and low notes never block, so the
fix loop cannot run forever. After MAX_ROUNDS the question goes to the founder.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import parsing
from phases.common import PhaseError, call, cell, json_from

ROLES = ("Code Reviewer", "Security Reviewer")
REQUIRED = ("verdict",)
SCHEMA = """{
  "verdict": "pass or changes",
  "summary": "one sentence",
  "issues": [{"severity": "high|medium|low", "file": "path", "problem": "what is wrong", "fix": "what to change"}]
}"""
MAX_ROUNDS = 2
DIFF_LIMIT = 26000
LOCKFILES = ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb")
SEVERITIES = ("high", "medium", "low")
MARKER = re.compile(r"<!--\s*review-round:(\d+)\s+sha:([0-9a-fA-F]*)\s*-->")


@dataclass
class ReviewResult:
    verdict: str
    summaries: dict = field(default_factory=dict)
    issues: list = field(default_factory=list)  # each: {reviewer, severity, file, problem, fix}
    skipped: list = field(default_factory=list)  # reviewers that gave no usable answer

    @property
    def blocking(self) -> list:
        return [i for i in self.issues if i["severity"] == "high"]


def trim_diff(diff: str, limit: int = DIFF_LIMIT) -> str:
    """The diff without lock files, capped. Lock files are huge and say nothing about the code."""
    parts = re.split(r"(?m)^(?=diff --git )", diff or "")
    kept, dropped = [], []
    for part in parts:
        head = part.split("\n", 1)[0]
        if head.startswith("diff --git ") and head.rstrip().endswith(LOCKFILES):
            dropped.append(head.split(" b/")[-1])
            continue
        kept.append(part)
    text = "".join(kept)
    if dropped:
        text += "\n(Lock files left out: " + ", ".join(dropped) + ")\n"
    if len(text) > limit:
        text = text[:limit] + "\n(The diff is cut here to fit.)\n"
    return text


def _issues(obj: dict, reviewer: str) -> list:
    found = []
    for raw in obj.get("issues") or []:
        if not isinstance(raw, dict):
            continue
        severity = str(raw.get("severity", "low")).strip().lower()
        found.append(
            {
                "reviewer": reviewer,
                "severity": severity if severity in SEVERITIES else "low",
                "file": str(raw.get("file", "")).strip(),
                "problem": str(raw.get("problem", "")).strip(),
                "fix": str(raw.get("fix", "")).strip(),
            }
        )
    return found


VERIFY_SCHEMA = """{"verdicts": [{"n": 1, "confirmed": true, "reason": "one sentence"}]}"""


def verify(result: ReviewResult, pr_title: str, task_text: str, diff: str, build_passed: bool) -> ReviewResult:
    """Second pass: a Review Verifier re-checks every high finding. Unproven ones become medium.

    LLM reviewers make confident mistakes; without this a wrong "high" would send Cursor on a wild goose chase.
    If the verifier cannot run, the findings stay as they were.
    """
    blocking = result.blocking
    if not blocking:
        return result
    listing = "\n".join(
        f"{n}. [{i['reviewer']}] {i['file']}: {i['problem']}" for n, i in enumerate(blocking, 1)
    )
    task = (
        "Double-check these high-severity code review findings. Answer with one fenced json block that "
        "matches this schema, one verdict per finding:\n" + VERIFY_SCHEMA + "\n\n"
        f"THE BUILD: {'the Vercel build passed, so the code compiles and deploys.' if build_passed else 'not known.'}\n"
        f"PULL REQUEST: {pr_title}\n\nTHE TASK:\n{(task_text or '(none)')[:3000]}\n\n"
        f"THE FINDINGS:\n{listing}\n\nTHE DIFF:\n{trim_diff(diff)}"
    )
    try:
        response = call("review_verify", task, "review-verify")
    except Exception as exc:  # a verifier failure must not block or lose the review
        print(f"Review verifier failed ({type(exc).__name__}); keeping the findings as they are.")
        return result
    parsed = parsing.find_json(response, required=("verdicts",))
    if not parsed:
        return result
    by_n = {}
    for item in parsed.get("verdicts") or []:
        if isinstance(item, dict):
            try:
                by_n[int(item.get("n"))] = item
            except (TypeError, ValueError):
                continue
    for n, issue in enumerate(blocking, 1):
        verdict = by_n.get(n)
        if verdict is not None and verdict.get("confirmed") is False:
            issue["severity"] = "medium"
            issue["problem"] += f" (Downgraded: not confirmed on re-check. {str(verdict.get('reason', '')).strip()})"
    result.verdict = "changes" if result.blocking else "pass"
    return result


def run(pr_title: str, task_text: str, diff: str, build_passed: bool = False) -> ReviewResult:
    task = (
        "Review this pull request. Each reviewer works alone and ends with one fenced json block that "
        "matches this schema:\n" + SCHEMA + "\n\n"
        f"PULL REQUEST: {pr_title}\n"
        f"THE BUILD: {'the Vercel build passed, so the code compiles and deploys.' if build_passed else 'not known.'}\n\n"
        f"THE TASK AND ITS ACCEPTANCE CRITERIA:\n{(task_text or '(no task file)')[:5000]}"
        "\n\nTHE DIFF:\n" + trim_diff(diff)
    )
    response = call("code_review", task, "code-review")

    result = ReviewResult(verdict="pass")
    for role in ROLES:
        try:
            obj = json_from(
                response, REQUIRED, SCHEMA, roles=[role], label="formatter-review-" + role.split()[0].lower()
            )
        except PhaseError:
            result.skipped.append(role)
            continue
        result.summaries[role] = str(obj.get("summary", "")).strip()
        result.issues += _issues(obj, role)
    if len(result.skipped) == len(ROLES):
        raise PhaseError("neither reviewer gave a usable answer")
    result.verdict = "changes" if result.blocking else "pass"
    return verify(result, pr_title, task_text, diff, build_passed)


def render(result: ReviewResult, round_n: int, sha: str, pr_link: str) -> str:
    icon = "PASS" if result.verdict == "pass" else "CHANGES REQUESTED"
    lines = [
        f"<!-- review-round:{round_n} sha:{sha} -->",
        f"**Code review (round {round_n}): {icon}**",
        "",
        "Two independent reviewers (Swarms `ConcurrentWorkflow`: Code Reviewer and Security Reviewer) read the diff; "
        "a Review Verifier re-checks every high-severity finding.",
        "",
    ]
    for role in ROLES:
        if role in result.summaries:
            lines.append(f"- **{role}**: {result.summaries[role] or 'no summary'}")
        else:
            lines.append(f"- **{role}**: no usable answer")
    if result.issues:
        lines += ["", "| Severity | Reviewer | File | Problem | Fix |", "|---|---|---|---|---|"]
        order = {s: i for i, s in enumerate(SEVERITIES)}
        for i in sorted(result.issues, key=lambda x: order[x["severity"]]):
            lines.append(
                f"| {i['severity']} | {cell(i['reviewer'])} | `{cell(i['file'])}` | {cell(i['problem'])} | {cell(i['fix'])} |"
            )
    else:
        lines += ["", "No problems found."]
    if result.verdict == "changes":
        lines += ["", f"Only high-severity problems block a PR. Cursor is asked to fix them (at most {MAX_ROUNDS} rounds)."]
    return "\n".join(lines)


def followup_prompt(pr_link: str, result: ReviewResult) -> str:
    """The exact text for the Cursor agent that opened the PR (event changes_requested)."""
    lines = [
        f"A code review of your pull request {pr_link} found problems that must be fixed before it can ship.",
        "Fix each one below in the same branch and push to this pull request. Do not open a new pull request and do not merge it.",
        "",
    ]
    for n, i in enumerate(result.blocking, 1):
        lines.append(f"{n}. {i['file'] or 'the code'}: {i['problem']} Fix: {i['fix'] or 'use your judgment'}")
    lines += ["", "Run the app, the build and the tests again before you push."]
    return "\n".join(lines)


def last_round(comments: list[dict]) -> tuple[int, str]:
    """(highest round so far, sha of the newest reviewed commit) read from our hidden markers."""
    best, sha = 0, ""
    for comment in comments or []:
        match = MARKER.search(comment.get("body") or "")
        if match and int(match.group(1)) >= best:
            best, sha = int(match.group(1)), match.group(2)
    return best, sha

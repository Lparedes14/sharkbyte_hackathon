"""Release Vote (/vote): a MajorityVoting swarm of four voters gives Go or No-Go.

Each voter's answer is read from its own entry in the Swarms output, so the vote table shows
every voter and its reason. The result is Go only when a strict majority says go AND two hard
gates hold: no unresolved high-severity review finding, and (for a PR with a UI) a QA result
that passed. The founder still gives the final Go in chat; this only says whether to ask.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import parsing
from phases.common import PhaseError, call, cell

VOTERS = ("QA Analyst", "Code Reviewer", "Security Reviewer", "Product Owner")
QA_LINE = re.compile(r"^\s*QA RESULT:\s*(PASS|FAIL)", re.IGNORECASE | re.MULTILINE)
GO_WORDS = {"go", "yes", "approve", "approved", "ship"}


@dataclass
class VoteResult:
    votes: list = field(default_factory=list)  # (voter, "go"|"no-go", reason)
    gates: list = field(default_factory=list)  # reasons a Go was blocked

    @property
    def go_count(self) -> int:
        return sum(1 for _, v, _ in self.votes if v == "go")

    @property
    def total(self) -> int:
        return len(self.votes)

    @property
    def go(self) -> bool:
        return self.go_count * 2 > self.total and not self.gates


def qa_verdict(comments: list[dict]) -> tuple[str | None, str]:
    """('pass'|'fail'|None, text) of the newest QA RESULT comment."""
    for comment in reversed(comments or []):
        body = comment.get("body") or ""
        match = QA_LINE.search(body)
        if match and body.lstrip().upper().startswith("QA RESULT"):
            return match.group(1).lower(), body
    return None, ""


def review_state(comments: list[dict]) -> tuple[str | None, str]:
    """('pass'|'changes'|None, text) of the newest code review comment."""
    for comment in reversed(comments or []):
        body = comment.get("body") or ""
        if "review-round:" in body and "Code review (round" in body:
            return ("pass" if "PASS" in body.split("\n")[1] else "changes"), body
    return None, ""


def already_voted(comments: list[dict]) -> bool:
    """True when a vote comment is newer than both the latest QA result and the latest code review."""
    last_vote = last_qa = last_review = -1
    for i, comment in enumerate(comments or []):
        body = comment.get("body") or ""
        if "Release vote:" in body and "MajorityVoting" in body:
            last_vote = i
        elif body.lstrip().upper().startswith("QA RESULT"):
            last_qa = i
        elif "review-round:" in body and "Code review (round" in body:
            last_review = i
    return last_vote > max(last_qa, last_review)


def run(
    pr_title: str,
    task_text: str,
    review_text: str,
    review_verdict: str | None,
    qa_text: str,
    qa_result: str | None,
    ui: bool,
    files: list[str],
) -> VoteResult:
    qa_part = qa_text[:3500] if qa_text else "(no QA result)"
    if not ui:
        qa_part = "This pull request changes no user interface, so QA by browser did not apply. " + qa_part
    task = (
        "Vote on whether this pull request is ready to release. Each voter answers alone with one fenced "
        'json block: {"vote": "go" or "no-go", "reason": "one sentence"}.\n\n'
        f"PULL REQUEST: {pr_title}\nFILES CHANGED: {', '.join(files[:25]) or '(unknown)'}\n\n"
        f"THE TASK:\n{(task_text or '(no task file)')[:3500]}\n\n"
        f"CODE REVIEW:\n{review_text[:3500] if review_text else '(no review yet)'}\n\n"
        f"QA RESULT:\n{qa_part}"
    )
    response = call("vote", task, "release-vote")

    result = VoteResult()
    for voter in VOTERS:
        obj = parsing.find_json(response, roles=[voter], required=("vote",))
        if obj is None:
            result.votes.append((voter, "no-go", "no valid vote"))
            continue
        word = str(obj.get("vote", "")).strip().lower()
        result.votes.append(
            (voter, "go" if word in GO_WORDS else "no-go", str(obj.get("reason", "")).strip() or "no reason given")
        )
    if len(result.votes) != len(VOTERS) or all(r == "no valid vote" for _, _, r in result.votes):
        raise PhaseError("the voters gave no usable answers")

    if review_verdict == "changes":
        result.gates.append("the code review still has high-severity findings")
    if ui and qa_result == "fail":
        result.gates.append("the QA Tester's result is FAIL")
    if ui and qa_result is None:
        result.gates.append("there is no QA result yet")
    return result


def render(result: VoteResult, pr_link: str) -> str:
    verdict = "GO" if result.go else "HOLD"
    lines = [
        f"**Release vote: {result.go_count}/{result.total} Go. Result: {verdict}.**",
        "",
        "Four voters (Swarms `MajorityVoting`) each gave Go or No-Go.",
        "",
        "| Voter | Vote | Reason |",
        "|---|---|---|",
    ]
    for voter, vote, reason in result.votes:
        lines.append(f"| {voter} | {'Go' if vote == 'go' else 'No-Go'} | {cell(reason)} |")
    if result.gates:
        lines += ["", "**Blocked, even with a majority:** " + "; ".join(result.gates) + "."]
    if result.go:
        lines += ["", 'Ready for your final Go. Tell Project Lead "Go" and it posts `/release`.']
    else:
        lines += ["", "Not releasing. Fix the points above and run `/vote` again, or `/release anyway` to override."]
    return "\n".join(lines)

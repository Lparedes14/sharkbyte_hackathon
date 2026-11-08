"""Orchestrator entry point (PLAN.md section 7).

GitHub Actions runs this on an issue comment. It reads the event file (user text never goes
through shell interpolation), accepts only commands from the repo owner, runs the matching
phase, then writes files, posts a comment, updates labels and calls Project Lead's webhook.

ORCH_CONTEXT tells it where it runs: "home" (home base, the Idea Inbox) or "project"
(a project repo, through template/.github/workflows/agent.yml).

Local runs, for development:
  python orchestrator/main.py --local                         health check, sends nothing
  python orchestrator/main.py --local-run idea_lab "<idea>"   prints the score card
  python orchestrator/main.py --local-run discovery "<idea>"  prints the PRD files
  python orchestrator/main.py --local-run design <PRD file>   prints the design file
  python orchestrator/main.py --local-run plan <folder with PRD.md and DESIGN.md>  prints the task files
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

import build
import github_io
import health
import notify
import state
from phases import design, discovery, idea_lab, plan
from phases.common import PhaseError, PhaseResult
from swarms_client import SwarmsError

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_LIMIT = 12000

COMMANDS = {
    "home": ("/ping", "/score", "/revise", "/approve", "/build"),
    "project": ("/ping", "/run", "/approve", "/revise"),
}


@dataclass
class Ctx:
    repo: str
    number: int
    issue: dict
    labels: set
    branch: str
    where: str  # "home" or "project"

    @property
    def link(self) -> str:
        return f"https://github.com/{self.repo}/issues/{self.number}"

    def comment(self, body: str) -> None:
        github_io.post_comment(self.repo, self.number, body)


# ---------- parsing the comment ----------


def parse_command(body: str) -> str:
    """Return the lowercase command word, like '/ping', or '' when the comment has none."""
    text = (body or "").strip()
    if not text:
        return ""
    first_word = text.splitlines()[0].split(maxsplit=1)[0]
    return first_word.lower() if first_word.startswith("/") else ""


def command_args(body: str) -> str:
    """Everything after the command word, without wrapping quotes. '/revise "x"' -> 'x'."""
    text = (body or "").strip()
    first_word = text.split(maxsplit=1)[0] if text else ""
    rest = text[len(first_word):].strip()
    if len(rest) >= 2 and rest[0] == rest[-1] and rest[0] in "\"'":
        rest = rest[1:-1].strip()
    return rest


# ---------- reading context ----------


def issue_context(ctx: Ctx) -> str:
    """The idea as the agents see it: title, body and the founder's non-command comments."""
    parts = [f"Title: {ctx.issue.get('title', '')}", "", ctx.issue.get("body") or "(no description)"]
    notes = []
    for c in github_io.list_comments(ctx.repo, ctx.number):
        user = c.get("user") or {}
        body = (c.get("body") or "").strip()
        if user.get("type") == "Bot" or not body or body.startswith("/"):
            continue
        notes.append(f"- {body}")
    if notes:
        parts += ["", "Comments from the founder:"] + notes
    if ctx.where == "project":
        idea_doc, _ = github_io.get_file(ctx.repo, "docs/IDEA.md", ctx.branch)
        if idea_doc:
            parts += ["", "docs/IDEA.md:", idea_doc]
    return "\n".join(parts)[:CONTEXT_LIMIT]


# ---------- applying a phase result ----------


def apply(ctx: Ctx, result: PhaseResult) -> None:
    for path, text in result.files.items():
        github_io.put_file(ctx.repo, path, text, result.commit_message or f"Update {path}", ctx.branch)
    for path in result.delete_paths:
        github_io.delete_file(ctx.repo, path, result.commit_message or f"Remove {path}", ctx.branch)

    body = result.comment
    if result.files:
        links = ", ".join(
            f"[{path}](https://github.com/{ctx.repo}/blob/{ctx.branch}/{path})" for path in result.files
        )
        body += f"\n\nFiles updated: {links}"
    ctx.comment(body)

    for label in result.add_labels:
        state.add(ctx.repo, ctx.number, ctx.labels, label)
    if result.phase:
        state.set_phase(ctx.repo, ctx.number, ctx.labels, result.phase)
    state.set_status(ctx.repo, ctx.number, ctx.labels, result.status)

    if result.notify_summary:
        payload = notify.make_payload(
            result.notify_event, ctx.repo, ctx.link, result.notify_summary, result.notify_question
        )
        ok, detail = notify.send("PROJECT_LEAD", payload)
        print(f"Project Lead webhook: {'ok' if ok else 'FAILED'} ({detail})")


def run_phase(ctx: Ctx, work) -> None:
    """Mark the issue as running, run the phase, then apply its result."""
    state.set_status(ctx.repo, ctx.number, ctx.labels, "running")
    apply(ctx, work())


# ---------- commands ----------


def cmd_ping(ctx: Ctx, args: str) -> None:
    results = health.run_all(repo=ctx.repo, link=ctx.link, send_webhooks=True)
    ctx.comment(health.format_comment(results, ctx.repo))
    for r in results:
        print(f"{'ok' if r.ok else 'FAILED'}: {r.name} - {r.detail}")


def cmd_score(ctx: Ctx, args: str) -> None:
    run_phase(ctx, lambda: idea_lab.run(issue_context(ctx), feedback=args or None))


def run_discovery(ctx: Ctx, feedback: str | None) -> None:
    def work() -> PhaseResult:
        previous = None
        if feedback:
            previous, _ = github_io.get_file(ctx.repo, "docs/PRD.md", ctx.branch)
        return discovery.run(issue_context(ctx), f"issue #{ctx.number}", feedback, previous)

    run_phase(ctx, work)


def run_design(ctx: Ctx, feedback: str | None) -> None:
    def work() -> PhaseResult:
        prd, _ = github_io.get_file(ctx.repo, "docs/PRD.md", ctx.branch)
        previous = None
        if feedback:
            previous, _ = github_io.get_file(ctx.repo, "docs/DESIGN.md", ctx.branch)
        return design.run(
            prd or "", f"issue #{ctx.number}", issue_context(ctx), feedback, previous
        )

    run_phase(ctx, work)


def run_plan(ctx: Ctx, feedback: str | None) -> None:
    def work() -> PhaseResult:
        prd, _ = github_io.get_file(ctx.repo, "docs/PRD.md", ctx.branch)
        design_doc, _ = github_io.get_file(ctx.repo, "docs/DESIGN.md", ctx.branch)
        previous = None
        if feedback:
            previous, _ = github_io.get_file(ctx.repo, "tasks/INDEX.md", ctx.branch)
        result = plan.run(prd or "", design_doc or "", f"issue #{ctx.number}", feedback, previous)
        # a new plan replaces the old task files, so none are left behind
        old = github_io.list_dir(ctx.repo, "tasks", ctx.branch)
        result.delete_paths = [p for p in old if p.endswith(".md") and p not in result.files]
        return result

    run_phase(ctx, work)


def cmd_run(ctx: Ctx, args: str) -> None:
    which = args.split()[0].lower() if args else ""
    if which == "discovery":
        run_discovery(ctx, feedback=None)
    elif which == "design":
        run_design(ctx, feedback=None)
    elif which == "plan":
        run_plan(ctx, feedback=None)
    elif which == "feature":
        ctx.comment("The `feature` phase is not built yet. Available now: `/run discovery`, `/run design`, `/run plan`.")
    else:
        ctx.comment("Tell me which phase to run: `/run discovery`, `/run design` or `/run plan`.")


def cmd_approve(ctx: Ctx, args: str) -> None:
    if state.status(ctx.labels) != "waiting-approval":
        ctx.comment("Nothing on this issue is waiting for approval right now.")
        return
    if "idea" in ctx.labels:
        ctx.comment(
            "To turn this idea into a project, tell Project Lead to build it. It confirms the repo "
            "name and visibility with you, then posts `/build <repo-name> public|private`."
        )
        return
    phase = state.phase(ctx.labels)
    if phase == "discovery":
        ctx.comment("PRD approved. Starting the Design phase now; the design arrives in about 2 minutes.")
        state.set_phase(ctx.repo, ctx.number, ctx.labels, "design")
        run_design(ctx, feedback=None)
        return
    if phase == "design":
        ctx.comment("Design and scope approved. Starting the Plan phase now; the task list arrives in about 2 minutes.")
        state.set_phase(ctx.repo, ctx.number, ctx.labels, "plan")
        run_plan(ctx, feedback=None)
        return
    if phase == "plan":
        state.set_phase(ctx.repo, ctx.number, ctx.labels, "build")
        state.set_status(ctx.repo, ctx.number, ctx.labels, None)
        ctx.comment(
            "Plan approved. This issue moves to the Build phase. "
            "Launching Cursor from here is not built yet, so nothing runs now."
        )
        return
    ctx.comment(f"Approval for the `{phase}` phase is not built yet.")


def cmd_revise(ctx: Ctx, args: str) -> None:
    if not args:
        ctx.comment('Add your feedback after the command, for example `/revise "make the quiz shorter"`.')
        return
    if state.status(ctx.labels) not in ("waiting-approval", "blocked"):
        ctx.comment("Nothing on this issue is waiting for approval, so there is nothing to revise.")
        return
    if "idea" in ctx.labels:
        cmd_score(ctx, args)
    elif state.phase(ctx.labels) == "discovery":
        run_discovery(ctx, feedback=args)
    elif state.phase(ctx.labels) == "design":
        run_design(ctx, feedback=args)
    elif state.phase(ctx.labels) == "plan":
        run_plan(ctx, feedback=args)
    else:
        ctx.comment(f"Revising the `{state.phase(ctx.labels)}` phase is not built yet.")


def cmd_build(ctx: Ctx, args: str) -> None:
    if "idea" not in ctx.labels:
        ctx.comment("`/build` works on Idea Inbox issues (label `idea`). Score the idea first with `/score`.")
        return
    state.set_status(ctx.repo, ctx.number, ctx.labels, "running")
    comments = github_io.list_comments(ctx.repo, ctx.number)
    try:
        result = build.create_project(ctx.repo, ctx.branch, ctx.issue, comments, args)
    except build.BuildError as exc:
        state.set_status(ctx.repo, ctx.number, ctx.labels, "blocked")
        ctx.comment(f"Could not create the project: {exc}.")
        return

    ctx.comment(build.report(result))
    state.add(ctx.repo, ctx.number, ctx.labels, "built")
    state.set_status(ctx.repo, ctx.number, ctx.labels, None)

    summary = f"Created {result.repo}, linked it to Vercel and started Deep Dive; the PRD arrives in about 2 minutes."
    question = ""
    if result.human_steps:
        summary = (
            f"Created {result.repo} and started Deep Dive; the PRD arrives in about 2 minutes. "
            "Steps that need a browser sign-in: " + " ".join(result.human_steps)
        )
        question = "Do these steps yourself if you can; otherwise tell me exactly what to click."
    payload = notify.make_payload("repo_created", result.repo, result.url, summary, question)
    ok, detail = notify.send("PROJECT_LEAD", payload)
    print(f"Project Lead webhook: {'ok' if ok else 'FAILED'} ({detail})")


HANDLERS = {
    "/ping": cmd_ping,
    "/score": cmd_score,
    "/run": cmd_run,
    "/approve": cmd_approve,
    "/revise": cmd_revise,
    "/build": cmd_build,
}


# ---------- event handling ----------


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
    comment = event.get("comment") or {}
    author = (comment.get("user") or {}).get("login", "")

    # Defense in depth: the workflow already checks this.
    if not owner or author != owner:
        print("Ignored: the comment is not from the repo owner.")
        return 0

    body = comment.get("body", "")
    command = parse_command(body)
    if not command:
        print("Ignored: the comment is not a command.")
        return 0

    os.environ["GITHUB_REPOSITORY"] = repo
    issue = event.get("issue") or {}
    where = os.environ.get("ORCH_CONTEXT", "home").strip() or "home"
    ctx = Ctx(
        repo=repo,
        number=issue.get("number"),
        issue=issue,
        labels=state.names(issue),
        branch=repository.get("default_branch") or "main",
        where=where,
    )

    allowed = COMMANDS.get(where, ())
    if command not in allowed:
        print(f"Ignored here: {command if command in HANDLERS else 'unknown command'}.")
        ctx.comment(
            "That command does not run here. Available here: "
            + ", ".join(f"`{c}`" for c in allowed)
            + "."
        )
        return 0

    print(f"Running {command} on {repo}#{ctx.number}")
    try:
        HANDLERS[command](ctx, command_args(body))
    except Exception as exc:  # report every failure on the issue, then fail the run
        traceback.print_exc()
        known = (PhaseError, SwarmsError, github_io.GitHubError, build.BuildError)
        reason = str(exc) if isinstance(exc, known) else type(exc).__name__
        try:
            ctx.comment(
                f"Something went wrong while running `{command}`: {reason}. "
                "The raw agent output is attached to the workflow run. Comment the command again to retry."
            )
            state.set_status(ctx.repo, ctx.number, ctx.labels, "blocked")
        except Exception:
            traceback.print_exc()
        return 1
    return 0


# ---------- local runs ----------


def run_local() -> int:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    results = health.run_all(repo=repo, link="(local run)", send_webhooks=False)
    print(health.format_comment(results, repo or "(GITHUB_REPOSITORY not set)"))
    return 0


def run_local_phase(name: str, idea: str) -> int:
    if name == "idea_lab":
        result = idea_lab.run(idea)
    elif name == "discovery":
        result = discovery.run(idea, "a local run")
    elif name == "plan":
        # the "idea" argument is a folder holding PRD.md and DESIGN.md
        folder = Path(idea)
        result = plan.run(
            (folder / "PRD.md").read_text(encoding="utf-8"),
            (folder / "DESIGN.md").read_text(encoding="utf-8"),
            "a local run",
        )
    elif name == "design":
        # the "idea" text is the PRD (or a path to a PRD file)
        path = Path(idea)
        result = design.run(path.read_text(encoding="utf-8") if path.is_file() else idea, "a local run")
    else:
        print("Use idea_lab, discovery, design or plan.")
        return 2
    print(result.comment)
    for path, text in result.files.items():
        print(f"\n===== {path} =====\n{text}")
    print(f"\n[labels: phase={result.phase} status={result.status} add={result.add_labels}]")
    print(f"[Project Lead would get: {result.notify_summary} / {result.notify_question}]")
    return 0


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    load_dotenv(ROOT / ".env")
    if argv[:1] == ["--local"]:
        return run_local()
    if argv[:1] == ["--local-run"] and len(argv) >= 3:
        return run_local_phase(argv[1], " ".join(argv[2:]))
    return run_event()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

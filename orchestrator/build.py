"""/build <repo-name> public|private: turn an idea into its own project (PLAN.md section 9, flow A).

Everything the GitHub API allows happens here, with GH_TOKEN:
  1. create the repo (with a README, so it has a main branch)
  2. copy home base's template/ into it (the agent workflow) and write docs/IDEA.md
  3. copy the Actions secrets (encrypted with the repo's public key)
  4. open the project issue and add the repo to projects.json in home base
  5. comment "/run discovery" on the project issue, which starts Deep Dive there

What GitHub cannot do (Vercel import, Vercel protection, Supabase) comes back as a checklist.
Project Lead does those steps in its browser when it can, and asks the human only when it can't.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

from nacl import encoding, public

import github_io

NAME_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")
SECRET_NAMES = (
    "SWARMS_API_KEY",
    "GH_TOKEN",
    "PROJECT_LEAD_WEBHOOK",
    "PROJECT_LEAD_WEBHOOK_KEY",
    "PROGRESS_REPORTER_WEBHOOK",
    "PROGRESS_REPORTER_WEBHOOK_KEY",
    "QA_TESTER_WEBHOOK",
    "QA_TESTER_WEBHOOK_KEY",
)
TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "template"
WORKFLOW_SETTLE_SECONDS = 10


class BuildError(Exception):
    """/build could not finish. The message is safe to post and says what to fix."""


@dataclass
class BuildResult:
    repo: str
    url: str
    private: bool
    issue_number: int
    done: list[str] = field(default_factory=list)
    human_steps: list[str] = field(default_factory=list)


def parse_args(args: str) -> tuple[str, bool]:
    parts = (args or "").split()
    if not parts:
        raise BuildError("give the repo name, for example `/build english-app public`")
    name = parts[0]
    visibility = parts[1].lower() if len(parts) > 1 else "public"
    if not NAME_RE.match(name):
        raise BuildError(f"'{name}' is not a valid repo name (letters, digits, '.', '-' and '_' only)")
    if visibility not in ("public", "private"):
        raise BuildError(f"visibility must be public or private, not '{visibility}'")
    return name, visibility == "private"


def encrypt_secret(public_key_b64: str, value: str) -> str:
    """GitHub requires secrets sealed with the repo's libsodium public key."""
    key = public.PublicKey(public_key_b64.encode("utf-8"), encoding.Base64Encoder())
    sealed = public.SealedBox(key).encrypt(value.encode("utf-8"))
    return base64.b64encode(sealed).decode("ascii")


def template_files() -> dict[str, str]:
    """Every file under template/, keyed by its path inside the new repo."""
    files = {}
    for path in sorted(TEMPLATE_DIR.rglob("*")):
        if path.is_file():
            files[path.relative_to(TEMPLATE_DIR).as_posix()] = path.read_text(encoding="utf-8")
    return files


def idea_doc(issue: dict, comments: list[dict], source_link: str) -> str:
    """docs/IDEA.md: the idea, the latest Idea Lab score card and the founder's answers."""
    score_card = ""
    answers = []
    for c in comments:
        body = (c.get("body") or "").strip()
        user = c.get("user") or {}
        if user.get("type") == "Bot" and body.startswith("Idea Lab score card"):
            score_card = body
        elif user.get("type") != "Bot" and body and not body.startswith("/"):
            answers.append(body)
        elif body.lower().startswith("/revise"):
            answers.append(body[len("/revise"):].strip().strip('"'))
    lines = [
        f"# Idea: {issue.get('title', '')}",
        "",
        f"_Copied from the Idea Inbox: {source_link}_",
        "",
        "## The idea",
        "",
        (issue.get("body") or "").strip() or "(no description)",
    ]
    if answers:
        lines += ["", "## The founder's answers and notes", ""] + [f"- {a}" for a in answers]
    if score_card:
        lines += ["", "## Idea Lab score card", "", score_card]
    return "\n".join(lines) + "\n"


def create_project(
    home_repo: str,
    home_branch: str,
    idea_issue: dict,
    idea_comments: list[dict],
    args: str,
) -> BuildResult:
    name, private = parse_args(args)
    token = os.environ.get("GH_TOKEN", "").strip()
    if not token:
        raise BuildError("GH_TOKEN is not set")

    title = idea_issue.get("title") or name
    source_link = idea_issue.get("html_url") or f"https://github.com/{home_repo}"

    # 1. Repo with a README, so main exists.
    try:
        repo = github_io.create_repo(name, private, title, token)
    except github_io.GitHubError as exc:
        raise BuildError(str(exc)) from None
    full = repo["full_name"]
    branch = repo.get("default_branch") or "main"
    result = BuildResult(repo=full, url=repo["html_url"], private=private, issue_number=0)
    result.done.append(f"Created the {'private' if private else 'public'} repo with a README")

    for _ in range(15):
        if github_io.branch_exists(full, branch, token):
            break
        time.sleep(2)

    # 2. Template files and the idea.
    for path, text in template_files().items():
        try:
            github_io.put_file(full, path, text, f"Add {path} from the home base template", branch, token)
        except github_io.GitHubError:
            if path.startswith(".github/workflows/"):
                raise BuildError(
                    "GH_TOKEN cannot write workflow files; give it Workflows: Read and write"
                ) from None
            raise
    github_io.put_file(full, "docs/IDEA.md", idea_doc(idea_issue, idea_comments, source_link),
                       "Add the idea from the Idea Inbox", branch, token)
    result.done.append("Added the agent workflow and docs/IDEA.md")

    # 3. Secrets.
    key = github_io.secrets_public_key(full, token)
    missing = []
    for secret in SECRET_NAMES:
        value = os.environ.get(secret, "").strip()
        if not value:
            missing.append(secret)
            continue
        github_io.put_secret(full, secret, encrypt_secret(key["key"], value), key["key_id"], token)
    copied = len(SECRET_NAMES) - len(missing)
    result.done.append(f"Copied {copied} of {len(SECRET_NAMES)} Actions secrets")
    if missing:
        result.human_steps.append(
            f"Add these secrets in {result.url}/settings/secrets/actions: " + ", ".join(missing)
        )

    # 4. Project issue and projects.json.
    issue_body = (
        f"{(idea_issue.get('body') or '').strip()}\n\n"
        f"Idea, score card and answers: [docs/IDEA.md]({result.url}/blob/{branch}/docs/IDEA.md). "
        f"From the Idea Inbox: {source_link}"
    )
    issue = github_io.create_issue(full, title, issue_body, token)
    result.issue_number = issue["number"]
    result.done.append(f"Opened the project issue #{issue['number']}")

    text, _ = github_io.get_file(home_repo, "projects.json", home_branch)
    try:
        projects = json.loads(text) if text else {}
    except ValueError:
        projects = {}
    projects[name] = result.url
    github_io.put_file(home_repo, "projects.json", json.dumps(projects, indent=2) + "\n",
                       f"Add {name} to projects.json", home_branch)
    result.done.append("Added it to projects.json")

    # 5. Start Deep Dive. GH_TOKEN, not GITHUB_TOKEN, so the comment starts the new repo's workflow.
    time.sleep(WORKFLOW_SETTLE_SECONDS)
    github_io.post_command(full, issue["number"], "/run discovery", token)
    result.done.append("Started Deep Dive on the project issue (the PRD arrives in about 2 minutes)")

    result.human_steps += [
        f"Vercel: Add New, then Project, import {full}, then Deploy (no build settings needed yet).",
        "Vercel: in that project's Settings, then Deployment Protection, turn off Require Log In, "
        "so QA Tester can open the previews.",
    ]
    return result


def report(result: BuildResult) -> str:
    """The comment on the idea issue. It starts with text, never with '/'."""
    lines = [
        f"Project created: [{result.repo}]({result.url}), project issue "
        f"[#{result.issue_number}]({result.url}/issues/{result.issue_number}).",
        "",
        "**Done automatically**",
    ]
    lines += [f"- ✅ {d}" for d in result.done]
    lines += [
        "",
        "**Steps that need a browser sign-in** (Project Lead tries these itself first, and asks you only if it can't)",
    ]
    lines += [f"{i}. {s}" for i, s in enumerate(result.human_steps, 1)]
    return "\n".join(lines)

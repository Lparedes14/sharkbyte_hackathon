"""Building from the plan: which task is next, and the prompt for the Cursor Cloud Agent.

State lives in GitHub, so nothing is stored here:
- a task file `tasks/NNN-<slug>.md` exists  -> the task is planned
- the issue has the label `task:NNN`        -> it was handed to Cursor ("launched")
- a PR titled `[task-NNN] ...` is open      -> Cursor delivered, waiting for review and merge
- that PR is merged                         -> the task is done
Tasks run one at a time, in order (PLAN.md section 10).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import github_io

TASK_FILE = re.compile(r"^tasks/(\d{3})-(.+)\.md$")
PR_TAG = re.compile(r"^\s*\[task-(\d+)\]", re.IGNORECASE)
PART_OF = re.compile(r"part of\s+#(\d+)", re.IGNORECASE)
DEPENDS = re.compile(r"Depends on:\s*([^.]*)\.")
HEADER_ISSUE = re.compile(r"\(issue #(\d+)\)")


@dataclass
class Task:
    n: int
    slug: str
    path: str
    title: str
    depends_on: list[int] = field(default_factory=list)
    issue: int | None = None  # the issue this task belongs to, read from the task file header


def parse_task(path: str, text: str) -> Task | None:
    match = TASK_FILE.match(path)
    if not match:
        return None
    heading = re.search(r"^#\s*Task\s*\d+:\s*(.+)$", text or "", re.MULTILINE)
    deps_line = DEPENDS.search(text or "")
    deps = [int(d) for d in re.findall(r"\d{3}", deps_line.group(1))] if deps_line else []
    n = int(match.group(1))
    issue = HEADER_ISSUE.search(text or "")
    return Task(
        n=n,
        slug=match.group(2),
        path=path,
        title=heading.group(1).strip() if heading else match.group(2).replace("-", " "),
        depends_on=[d for d in deps if d < n],
        issue=int(issue.group(1)) if issue else None,
    )


def list_tasks(repo: str, branch: str) -> list[Task]:
    tasks = []
    for path in sorted(github_io.list_dir(repo, "tasks", branch)):
        if not TASK_FILE.match(path):
            continue
        text, _ = github_io.get_file(repo, path, branch)
        task = parse_task(path, text or "")
        if task:
            tasks.append(task)
    return sorted(tasks, key=lambda t: t.n)


def tasks_of_issue(all_tasks: list[Task], number: int, is_feature: bool) -> list[Task]:
    """The tasks that belong to one issue. Old task files without an issue belong to the project issue."""
    return [t for t in all_tasks if t.issue == number or (t.issue is None and not is_feature)]


def task_file_for(repo: str, n: int, branch: str) -> str | None:
    """The path of tasks/NNN-*.md, or None."""
    for path in github_io.list_dir(repo, "tasks", branch):
        match = TASK_FILE.match(path)
        if match and int(match.group(1)) == n:
            return path
    return None


def pr_task_number(title: str) -> int | None:
    match = PR_TAG.match(title or "")
    return int(match.group(1)) if match else None


def pr_issue_number(body: str) -> int | None:
    match = PART_OF.search(body or "")
    return int(match.group(1)) if match else None


def pr_kind(pr: dict) -> str:
    if pr.get("merged_at"):
        return "merged"
    return "open" if pr.get("state") == "open" else "closed"


def task_prs(prs: list[dict], since: str | None) -> dict[int, dict]:
    """The PR that counts for each task: a merged one, else an open one, else a closed one.

    PRs created before the plan was written (`since`) are ignored: they come from earlier tests.
    """
    rank = {"merged": 3, "open": 2, "closed": 1}
    best: dict[int, dict] = {}
    for pr in prs:
        n = pr_task_number(pr.get("title", ""))
        if n is None:
            continue
        if since and (pr.get("created_at") or "") < since:
            continue
        if n not in best or rank[pr_kind(pr)] > rank[pr_kind(best[n])]:
            best[n] = pr
    return best


def launched_numbers(labels: set[str]) -> set[int]:
    return {int(x.split(":", 1)[1]) for x in labels if re.fullmatch(r"task:\d+", x)}


def statuses(tasks: list[Task], prs: dict[int, dict], launched: set[int]) -> dict[int, str]:
    """merged | open | launched | none for each task number."""
    result = {}
    for t in tasks:
        kind = pr_kind(prs[t.n]) if t.n in prs else None
        if kind in ("merged", "open"):
            result[t.n] = kind
        elif t.n in launched and kind is None:
            result[t.n] = "launched"
        else:
            result[t.n] = "none"  # never started, or its PR was closed without merging
    return result


def next_task(tasks: list[Task], status: dict[int, str], again: bool = False) -> tuple[Task | None, str]:
    """(task to launch, why not). `why` is one of: ok, all-merged, in-progress, blocked."""
    in_progress = [t for t in tasks if status[t.n] in ("open", "launched")]
    if again:
        waiting = [t for t in in_progress if status[t.n] == "launched"]
        if waiting:
            return waiting[0], "ok"
    if in_progress:
        return None, "in-progress"
    if all(status[t.n] == "merged" for t in tasks):
        return None, "all-merged"
    for t in tasks:
        if status[t.n] == "none" and all(status.get(d) == "merged" for d in t.depends_on):
            return t, "ok"
    return None, "blocked"


def cursor_prompt(repo: str, task: Task, issue_number: int) -> str:
    """The exact text Project Lead gives a Cursor Cloud Agent (PLAN.md section 10)."""
    return (
        f"Repository: https://github.com/{repo} (branch main)\n"
        f"Read .cursor/rules/project.mdc and {task.path} first, then docs/PRD.md and docs/DESIGN.md.\n"
        "Implement only that task. Run the app, the build and the tests before you finish.\n"
        f'Open a pull request into main titled "[task-{task.n:03d}] {task.title}". '
        f'The description must start with "Part of #{issue_number}" and then list how you checked '
        "each acceptance criterion in the task file.\n"
        "Do not merge the pull request. Never commit secrets or .env files."
    )


def find_issue(repo: str, pr_body: str, token: str | None = None) -> dict | None:
    """The project issue a PR belongs to: the one named in 'Part of #N', else the open build issue."""
    number = pr_issue_number(pr_body)
    if number:
        try:
            issue = github_io.get_issue(repo, number, token)
            if "pull_request" not in issue:
                return issue
        except github_io.GitHubError:
            pass
    for label in ("phase:build", "phase:plan"):
        found = github_io.list_open_issues_with_label(repo, label, token)
        if found:
            return found[0]
    return None

"""Plan (/run plan, and automatically after the design is approved): split the design into tasks.

A SequentialWorkflow runs the Tech Lead, then the Cursor Prompt Writer. The Prompt Writer gives
the plan as JSON; the orchestrator renders tasks/NNN-<slug>.md, tasks/INDEX.md and
.cursor/rules/project.mdc from it, so the files always have the same layout. Cursor Cloud Agents
build one task at a time, in order.
"""

from __future__ import annotations

import re

from phases.common import PhaseError, PhaseResult, as_list, call, cell, json_from

REQUIRED = ("tasks",)
SCHEMA = """{
  "rules": {
    "stack": ["technology and version"],
    "layout": ["folder and what it holds"],
    "conventions": ["rule every agent follows"],
    "commands": {"install": "cmd", "dev": "cmd", "test": "cmd", "build": "cmd"},
    "never": ["thing agents must never do"]
  },
  "tasks": [
    {"id": 1, "slug": "short-kebab-name", "title": "short title", "goal": "one or two sentences",
     "stories": ["US-1"], "depends_on": [],
     "files": ["path/to/file"],
     "steps": ["concrete step"],
     "acceptance_criteria": ["observable result a tester can check in a browser"],
     "done_when": "one sentence",
     "out_of_scope": ["thing not to do in this task"]}
  ]
}"""
MAX_TASKS = 8


def _dicts(value) -> list[dict]:
    return [item for item in (value or []) if isinstance(item, dict)]


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return slug[:40].strip("-") or "task"


def normalize_tasks(plan: dict) -> list[dict]:
    """Clean tasks: numbered 1..n in order, unique slugs, depends_on pointing only at earlier tasks."""
    tasks = []
    used: set[str] = set()
    ids: dict[str, int] = {}
    for i, raw in enumerate(_dicts(plan.get("tasks"))[:MAX_TASKS], 1):
        title = str(raw.get("title", "")).strip() or f"Task {i}"
        slug = slugify(raw.get("slug") or title)
        while slug in used:
            slug += f"-{i}"
        used.add(slug)
        ids[str(raw.get("id", i)).strip()] = i
        tasks.append(
            {
                "n": i,
                "slug": slug,
                "title": title,
                "goal": str(raw.get("goal", "")).strip(),
                "stories": as_list(raw.get("stories")),
                "raw_depends": as_list(raw.get("depends_on")),
                "files": as_list(raw.get("files")),
                "steps": as_list(raw.get("steps")),
                "criteria": as_list(raw.get("acceptance_criteria")),
                "done_when": str(raw.get("done_when", "")).strip(),
                "out_of_scope": as_list(raw.get("out_of_scope")),
            }
        )
    for task in tasks:
        deps = []
        for ref in task.pop("raw_depends"):
            n = ids.get(str(ref).strip().lstrip("#"))
            if n and n < task["n"] and n not in deps:
                deps.append(n)
        if not deps and task["n"] > 1:
            deps = [task["n"] - 1]  # tasks run one at a time, so the safe default is the one before
        task["depends_on"] = deps
    return tasks


def task_path(task: dict) -> str:
    return f"tasks/{task['n']:03d}-{task['slug']}.md"


def render_task(task: dict, product: str, issue_ref: str) -> str:
    def block(title: str, items: list[str], boxes: bool = False) -> list[str]:
        mark = "- [ ] " if boxes else "- "
        return ["", f"## {title}"] + ([f"{mark}{i}" for i in items] if items else ["- None"])

    deps = ", ".join(f"task {d:03d}" for d in task["depends_on"]) or "none"
    lines = [
        f"# Task {task['n']:03d}: {task['title']}",
        "",
        f"_Part of {product} ({issue_ref}). Depends on: {deps}. Stories: "
        f"{', '.join(task['stories']) or 'none listed'}._",
        "",
        "Read `.cursor/rules/project.mdc`, `docs/PRD.md` and `docs/DESIGN.md` first. "
        "Implement only this task.",
        "",
        "## Goal",
        "",
        task["goal"] or "See the steps below.",
    ]
    lines += block("Files to touch", [f"`{f}`" for f in task["files"]])
    lines += ["", "## Steps"] + [f"{i}. {s}" for i, s in enumerate(task["steps"], 1)] if task["steps"] else ["", "## Steps", "- None"]
    lines += block("Acceptance criteria", task["criteria"], boxes=True)
    lines += ["", "## Done when", "", task["done_when"] or "All acceptance criteria above pass and the app builds."]
    lines += block("Out of scope", task["out_of_scope"])
    lines += [
        "",
        "## Pull request",
        "",
        f"Title: `[task-{task['n']:03d}] {task['title']}`. The description says `Part of {issue_ref}`. "
        "Run the app and the tests before you open the PR.",
    ]
    return "\n".join(lines) + "\n"


def render_index(tasks: list[dict], product: str, issue_ref: str) -> str:
    lines = [
        f"# Tasks: {product}",
        "",
        f"_Written by the Plan swarm (Swarms `SequentialWorkflow`: Tech Lead, then Cursor Prompt Writer) for {issue_ref}. "
        "Cursor builds one task at a time, in this order._",
        "",
        "| # | Task | Depends on | Stories | File |",
        "|---|---|---|---|---|",
    ]
    for t in tasks:
        deps = ", ".join(f"{d:03d}" for d in t["depends_on"]) or "-"
        lines.append(
            f"| {t['n']:03d} | {cell(t['title'])} | {deps} | {cell(', '.join(t['stories']) or '-')} | `{task_path(t)}` |"
        )
    return "\n".join(lines) + "\n"


def render_rules(plan: dict, product: str) -> str:
    rules = plan.get("rules") if isinstance(plan.get("rules"), dict) else {}
    commands = rules.get("commands") if isinstance(rules.get("commands"), dict) else {}
    lines = [
        "---",
        f"description: Project rules for {product}",
        "alwaysApply: true",
        "---",
        "",
        f"# {product}: rules for every coding agent",
        "",
        "You work on one task file at a time from `tasks/`. Read `docs/PRD.md` and `docs/DESIGN.md` first.",
    ]
    for title, key in (("Stack", "stack"), ("Folder layout", "layout"), ("Conventions", "conventions")):
        lines += ["", f"## {title}"] + [f"- {i}" for i in as_list(rules.get(key))] or [""]
    lines += ["", "## Commands"]
    lines += [f"- {name}: `{cmd}`" for name, cmd in commands.items() if str(cmd).strip()] or ["- See the task file"]
    lines += ["", "## Never"] + [f"- {i}" for i in as_list(rules.get("never"))]
    lines += [
        "- Never commit secrets, API keys or `.env` files; read configuration from environment variable names.",
        "- Never change files outside the current task's scope.",
        "- Open one PR per task titled `[task-NNN] <title>` with `Part of #<issue number>` in the description.",
    ]
    return "\n".join(lines) + "\n"


def run(
    prd: str,
    design: str,
    issue_ref: str,
    feedback: str | None = None,
    previous_index: str | None = None,
) -> PhaseResult:
    if not prd.strip() or not design.strip():
        raise PhaseError("the plan needs the approved PRD (docs/PRD.md) and design (docs/DESIGN.md)")

    task = (
        "Plan the build of this product. The Tech Lead splits the design into small tasks; the "
        "Cursor Prompt Writer then writes the Cursor-ready task prompts and the project rules and "
        "gives the final answer, ending with one fenced json block that matches this schema:\n"
        + SCHEMA
        + f"\n\nRules: 3 to 6 tasks (never more than {MAX_TASKS}), in build order; each task is one "
        "pull request; ids are 1, 2, 3 in order and depends_on lists earlier ids; every user story "
        "is covered; copy the PRD's acceptance criteria into the task that delivers them; list real "
        "file paths from the design; never write secret values.\n\n"
        "APPROVED PRD:\n" + prd[-7000:] + "\n\nAPPROVED DESIGN:\n" + design[-9000:]
    )
    if previous_index:
        task += "\n\nTHE PREVIOUS TASK LIST (revise it, do not start over):\n" + previous_index[-3000:]
    if feedback:
        task += "\n\nTHE FOUNDER'S FEEDBACK (apply it):\n" + feedback

    response = call("plan", task, "plan")
    plan = json_from(
        response, REQUIRED, SCHEMA, roles=["Cursor Prompt Writer"], any_role_fallback=True, label="formatter-plan"
    )
    tasks = normalize_tasks(plan)
    if not tasks:
        raise PhaseError("the plan has no tasks")

    match = re.search(r"^#\s*PRD:\s*(.+)$", prd, re.MULTILINE)
    product = match.group(1).strip() if match else "the product"
    covered = {s for t in tasks for s in t["stories"]}
    story_ids = set(re.findall(r"^### (US-\d+)", prd, re.MULTILINE))
    missing = sorted(story_ids - covered)

    files = {task_path(t): render_task(t, product, issue_ref) for t in tasks}
    files["tasks/INDEX.md"] = render_index(tasks, product, issue_ref)
    files[".cursor/rules/project.mdc"] = render_rules(plan, product)

    lines = [
        "Plan ready from the Plan swarm (Swarms `SequentialWorkflow`: the Tech Lead split the design, "
        "then the Cursor Prompt Writer wrote the task prompts and project rules).",
        "",
        f"**{product}**: {len(tasks)} tasks. Cursor builds them one at a time, in this order.",
        "",
        "| # | Task | Depends on | Stories |",
        "|---|---|---|---|",
    ]
    for t in tasks:
        deps = ", ".join(f"{d:03d}" for d in t["depends_on"]) or "-"
        lines.append(f"| {t['n']:03d} | {cell(t['title'])} | {deps} | {cell(', '.join(t['stories']) or '-')} |")
    if missing:
        lines += ["", f"**Heads up:** no task lists {', '.join(missing)}. Ask for a revision if that story should be built."]
    lines += [
        "",
        'Reply "Go" to Project Lead to approve the plan (it posts `/approve`), or say what to change '
        "(it posts `/revise`).",
    ]

    revised = " (revised)" if feedback else ""
    summary = f"Plan ready{revised}: {product}, {len(tasks)} tasks: " + "; ".join(
        f"{t['n']}. {t['title']}" for t in tasks
    ) + "."
    if missing:
        summary += f" No task covers {', '.join(missing)}."
    return PhaseResult(
        comment="\n".join(lines),
        files=files,
        commit_message=f"Plan: write {len(tasks)} task prompts and the project rules{revised}",
        phase="plan",
        status="waiting-approval",
        notify_summary=summary,
        notify_question="Approve the plan so Cursor can start building? Reply Go, or tell me what to change.",
    )

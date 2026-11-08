"""Design (/run design, and automatically after the PRD is approved): a GroupChat debates the design.

The Architect, UX/UI Designer, Security Reviewer and MVP Cutter discuss the approved PRD. The
MVP Cutter gives the final answer as JSON; the orchestrator renders docs/DESIGN.md from it, so
the file always has the same layout. The Plan phase reads that file to write the Cursor tasks.
"""

from __future__ import annotations

import re

from phases.common import PhaseError, PhaseResult, as_list, call, cell, json_from

REQUIRED = ("title", "stack", "pages", "scope_in")
SCHEMA = """{
  "title": "short product name",
  "summary": "two sentences: what gets built and how",
  "stack": [{"layer": "Frontend | Backend | Database | Hosting | ...", "choice": "technology", "why": "one line"}],
  "pages": [{"route": "/path", "purpose": "what the user does here", "components": ["component"], "stories": ["US-1"]}],
  "data_model": [{"table": "table_name", "purpose": "what it stores", "columns": ["name type notes"]}],
  "api": ["METHOD /path: what it does (leave empty if the app talks to Supabase directly)"],
  "security": ["rule that must hold, for example 'RLS on every table'"],
  "env_vars": ["VARIABLE_NAME (names only, never values)"],
  "decisions": [{"topic": "question from the PRD or a trade-off", "decision": "what we chose", "why": "one line"}],
  "scope_in": ["what the MVP builds"],
  "scope_out": ["what it does not build now"],
  "risks": ["risk and how to reduce it"],
  "human_steps": ["step only a human can do, with the exact place to click"],
  "open_questions": ["real choice for the founder"]
}"""


def prd_title(prd: str) -> str:
    """The product name from the PRD's first heading, '# PRD: <name>'."""
    match = re.search(r"^#\s*PRD:\s*(.+)$", prd or "", re.MULTILINE)
    return match.group(1).strip() if match else ""


def _dicts(value) -> list[dict]:
    return [item for item in (value or []) if isinstance(item, dict)]


def _bullets(title: str, items: list[str]) -> list[str]:
    return ["", f"## {title}"] + ([f"- {item}" for item in items] if items else ["- None"])


def render_design(design: dict, issue_ref: str) -> str:
    title = str(design.get("title", "Product")).strip()
    lines = [
        f"# Design: {title}",
        "",
        f"_Written by the Design swarm (Swarms `GroupChat`: Architect, UX/UI Designer, Security "
        f"Reviewer and MVP Cutter) for {issue_ref}, from the approved PRD._",
        "",
        str(design.get("summary", "")).strip(),
        "",
        "## Stack",
        "",
        "| Layer | Choice | Why |",
        "|---|---|---|",
    ]
    for row in _dicts(design.get("stack")):
        lines.append(f"| {cell(row.get('layer', ''))} | {cell(row.get('choice', ''))} | {cell(row.get('why', ''))} |")

    lines += ["", "## Pages", "", "| Route | Purpose | Components | Stories |", "|---|---|---|---|"]
    for row in _dicts(design.get("pages")):
        lines.append(
            f"| `{cell(row.get('route', ''))}` | {cell(row.get('purpose', ''))} | "
            f"{cell(', '.join(as_list(row.get('components'))))} | {cell(', '.join(as_list(row.get('stories'))))} |"
        )

    lines += ["", "## Data model"]
    tables = _dicts(design.get("data_model"))
    for table in tables:
        lines += ["", f"### `{str(table.get('table', '')).strip()}`", "", str(table.get("purpose", "")).strip(), ""]
        lines += [f"- `{c}`" for c in as_list(table.get("columns"))]
    if not tables:
        lines += ["", "- No database tables."]

    lines += _bullets("API routes", as_list(design.get("api")))
    lines += _bullets("Security rules", as_list(design.get("security")))
    lines += _bullets("Environment variables (names only)", [f"`{v}`" for v in as_list(design.get("env_vars"))])

    lines += ["", "## Decisions", "", "| Topic | Decision | Why |", "|---|---|---|"]
    for row in _dicts(design.get("decisions")):
        lines.append(f"| {cell(row.get('topic', ''))} | {cell(row.get('decision', ''))} | {cell(row.get('why', ''))} |")

    lines += _bullets("Scope: in", as_list(design.get("scope_in")))
    lines += _bullets("Scope: out", as_list(design.get("scope_out")))
    lines += _bullets("Risks", as_list(design.get("risks")))
    lines += _bullets("Steps only a human can do", as_list(design.get("human_steps")))
    lines += _bullets("Open questions", as_list(design.get("open_questions")))
    return "\n".join(lines) + "\n"


def run(
    prd: str,
    issue_ref: str,
    context: str = "",
    feedback: str | None = None,
    previous_design: str | None = None,
) -> PhaseResult:
    if not prd.strip():
        raise PhaseError("there is no approved PRD (docs/PRD.md) to design from")

    task = (
        "Design a small MVP for the approved PRD below. Debate it as a group: the Architect proposes, "
        "the UX/UI Designer and Security Reviewer challenge, and the MVP Cutter gives the final "
        "answer, ending with one fenced json block that matches this design schema:\n"
        + SCHEMA
        + "\n\nRules: the title is the product name from the PRD"
        + (f" ({prd_title(prd)})" if prd_title(prd) else "")
        + ", never an agent name. Persist data in Supabase (Postgres) by default, so progress and "
        "history survive across days and devices; use browser-only storage only if the PRD or the "
        "founder context says the data may live on the device only. If the app has no accounts, use "
        "Supabase anonymous sign-in so every device still gets its own user and Row Level Security "
        "can protect the rows. When the design uses Supabase, human_steps must say: create the "
        "Supabase project, turn on Anonymous sign-ins, run the migration that the build writes "
        "under supabase/migrations in the Supabase SQL editor, and add the environment variable "
        "names in the Vercel project settings. Keep the stack small; every user story must be reachable from a page; every "
        "acceptance criterion must be checkable by a tester who opens the public Vercel preview "
        "in a browser; the preview has no sign-in unless the PRD needs accounts; 3 to 6 decisions; "
        "never write secret values, only environment variable names.\n\n"
        "APPROVED PRD:\n" + prd[-9000:]
    )
    if context:
        task += "\n\nFOUNDER CONTEXT:\n" + context[:3000]
    if previous_design:
        task += "\n\nTHE PREVIOUS DESIGN (revise it, do not start over):\n" + previous_design[-8000:]
    if feedback:
        task += "\n\nTHE FOUNDER'S FEEDBACK (apply it):\n" + feedback

    response = call("design", task, "design")
    design = json_from(
        response, REQUIRED, SCHEMA, roles=["MVP Cutter"], any_role_fallback=True, label="formatter-design"
    )

    title = prd_title(prd) or str(design.get("title", "Product")).strip()
    design["title"] = title
    stack = _dicts(design.get("stack"))
    pages = _dicts(design.get("pages"))
    tables = _dicts(design.get("data_model"))
    scope_in = as_list(design.get("scope_in"))
    scope_out = as_list(design.get("scope_out"))
    human_steps = as_list(design.get("human_steps"))
    open_questions = as_list(design.get("open_questions"))
    if not stack or not pages:
        raise PhaseError("the design has no stack or no pages")

    lines = [
        "Design ready from the Design swarm (Swarms `GroupChat`: Architect, UX/UI Designer, "
        "Security Reviewer and MVP Cutter debated it).",
        "",
        f"**{title}**: {len(stack)} stack choices, {len(pages)} pages, {len(tables)} tables.",
        "",
        "**Stack**: " + "; ".join(f"{cell(r.get('layer', ''))}: {cell(r.get('choice', ''))}" for r in stack),
        "",
        "**In scope**",
    ] + [f"- {item}" for item in scope_in]
    if scope_out:
        lines += ["", "**Left out for now**"] + [f"- {item}" for item in scope_out]
    if human_steps:
        lines += ["", "**Only you can do**"] + [f"- {item}" for item in human_steps]
    if open_questions:
        lines += ["", "**Open questions**"] + [f"- {q}" for q in open_questions]
    lines += [
        "",
        'Reply "Go" to Project Lead to approve the design and scope (it posts `/approve`), or say '
        "what to change (it posts `/revise`).",
    ]

    revised = " (revised)" if feedback else ""
    summary = (
        f"Design ready{revised}: {title}. Stack: "
        + ", ".join(str(r.get("choice", "")).strip() for r in stack[:4] if r.get("choice"))
        + f". {len(pages)} pages, {len(tables)} tables; {len(scope_out)} things left out of the first version."
    )
    if human_steps:
        summary += " Only you can do (later, not now): " + "; ".join(human_steps[:4]) + "."
    return PhaseResult(
        comment="\n".join(lines),
        files={"docs/DESIGN.md": render_design(design, issue_ref)},
        commit_message=f"Design: write the architecture and scope{revised}",
        phase="design",
        status="waiting-approval",
        notify_summary=summary,
        notify_question="Approve the design and scope? Reply Go, or tell me what to change.",
    )

"""Deep Dive (/run discovery): a HierarchicalSwarm writes the PRD and the acceptance criteria.

The Swarms director coordinates the Product Owner, Product Manager and UX Researcher.
The Product Owner gives the final PRD as JSON; the orchestrator renders docs/PRD.md and
docs/ACCEPTANCE.md from it, so the files always have the same layout.
"""

from __future__ import annotations

from phases.common import PhaseError, PhaseResult, as_list, call, cell, json_from

REQUIRED = ("title", "user_stories")
SCHEMA = """{
  "title": "short product name",
  "problem": "one paragraph",
  "users": ["persona in one line"],
  "goals": ["goal"],
  "user_stories": [
    {"id": "US-1", "as_a": "type of user", "i_want": "what they do", "so_that": "why",
     "acceptance_criteria": ["observable result a tester can check in a browser"]}
  ],
  "out_of_scope": ["thing we will not build now"],
  "success_metrics": ["metric"],
  "open_questions": ["question for the founder"]
}"""


def _stories(prd: dict) -> list[dict]:
    stories = []
    for i, raw in enumerate(prd.get("user_stories") or [], 1):
        story = raw if isinstance(raw, dict) else {"i_want": str(raw)}
        stories.append(
            {
                "id": str(story.get("id") or f"US-{i}").strip(),
                "as_a": str(story.get("as_a", "")).strip(),
                "i_want": str(story.get("i_want", "")).strip(),
                "so_that": str(story.get("so_that", "")).strip(),
                "criteria": as_list(story.get("acceptance_criteria")),
            }
        )
    return stories


def _section(title: str, items: list[str]) -> list[str]:
    return ["", f"## {title}"] + ([f"- {item}" for item in items] if items else ["- None yet"])


def _story_line(story: dict) -> str:
    parts = []
    if story["as_a"]:
        parts.append(f"**As a** {story['as_a']}")
    if story["i_want"]:
        parts.append(f"**I want** {story['i_want']}")
    if story["so_that"]:
        parts.append(f"**so that** {story['so_that']}")
    return ", ".join(parts) + "."


def render_prd(prd: dict, stories: list[dict], issue_ref: str) -> str:
    title = str(prd.get("title", "Product")).strip()
    lines = [
        f"# PRD: {title}",
        "",
        f"_Written by the Deep Dive swarm (Swarms `HierarchicalSwarm`: Product Owner, Product Manager "
        f"and UX Researcher, coordinated by a director) for {issue_ref}._",
        "",
        "## Problem",
        "",
        str(prd.get("problem", "")).strip() or "Not stated yet.",
    ]
    lines += _section("Users", as_list(prd.get("users")))
    lines += _section("Goals", as_list(prd.get("goals")))
    lines += ["", "## User stories"]
    for story in stories:
        lines += ["", f"### {story['id']}", "", _story_line(story), "", "Acceptance criteria:"]
        lines += [f"- [ ] {c}" for c in story["criteria"]] or ["- [ ] (none yet)"]
    lines += _section("Out of scope", as_list(prd.get("out_of_scope")))
    lines += _section("Success metrics", as_list(prd.get("success_metrics")))
    lines += _section("Open questions", as_list(prd.get("open_questions")))
    return "\n".join(lines) + "\n"


def render_acceptance(prd: dict, stories: list[dict]) -> str:
    title = str(prd.get("title", "Product")).strip()
    lines = [
        f"# Acceptance criteria: {title}",
        "",
        "QA Tester checks each item on the preview, like a real user, and reports pass or fail on the PR.",
    ]
    for story in stories:
        lines += ["", f"## {story['id']}", "", _story_line(story), ""]
        lines += [f"- [ ] {c}" for c in story["criteria"]] or ["- [ ] (none yet)"]
    return "\n".join(lines) + "\n"


def run(context: str, issue_ref: str, feedback: str | None = None, previous_prd: str | None = None) -> PhaseResult:
    task = (
        "Turn this product idea into a PRD for a small MVP.\n\n"
        "The Product Owner gives the final answer, ending with one fenced json block that "
        "matches this PRD schema:\n" + SCHEMA + "\n\n"
        "Rules: 3 to 6 user stories; each story has 2 to 4 acceptance criteria that a tester can "
        "check in a browser; keep the scope small; put anything unclear in open_questions.\n\n"
        "IDEA AND DISCUSSION:\n" + context
    )
    if previous_prd:
        task += "\n\nTHE PREVIOUS PRD (revise it, do not start over):\n" + previous_prd[-8000:]
    if feedback:
        task += "\n\nTHE FOUNDER'S FEEDBACK (apply it):\n" + feedback

    response = call("deep_dive", task, "deep-dive")
    prd = json_from(
        response, REQUIRED, SCHEMA, roles=["Product Owner"], any_role_fallback=True, label="formatter-prd"
    )
    stories = _stories(prd)
    if not stories:
        raise PhaseError("the PRD has no user stories")

    criteria_count = sum(len(s["criteria"]) for s in stories)
    title = str(prd.get("title", "Product")).strip()
    open_questions = as_list(prd.get("open_questions"))

    lines = [
        "PRD ready from the Deep Dive swarm (Swarms `HierarchicalSwarm`: a director coordinated the "
        "Product Owner, Product Manager and UX Researcher).",
        "",
        f"**{title}**: {len(stories)} user stories, {criteria_count} acceptance criteria.",
        "",
        "| Story | I want | Criteria |",
        "|---|---|---|",
    ]
    for story in stories:
        lines.append(f"| {cell(story['id'])} | {cell(story['i_want'])} | {len(story['criteria'])} |")
    if open_questions:
        lines += ["", "**Open questions**"] + [f"- {q}" for q in open_questions]
    lines += [
        "",
        'Reply "Go" to Project Lead to approve (it posts `/approve`), or say what to change '
        "(it posts `/revise`).",
    ]

    revised = " (revised)" if feedback else ""
    return PhaseResult(
        comment="\n".join(lines),
        files={
            "docs/PRD.md": render_prd(prd, stories, issue_ref),
            "docs/ACCEPTANCE.md": render_acceptance(prd, stories),
        },
        commit_message=f"Deep Dive: write the PRD and acceptance criteria{revised}",
        phase="discovery",
        status="waiting-approval",
        notify_summary=(
            f"PRD ready{revised}: {title}, {len(stories)} user stories, {criteria_count} acceptance criteria."
        ),
        notify_question="Approve the PRD? Reply Go, or tell me what to change.",
    )

"""Feature story (/run feature): the fast path for a new feature on an existing product.

A SequentialWorkflow: the Product Owner writes the story from the founder's request and the
product's PRD and design, then the MVP Cutter trims it. The result is docs/features/<N>-<slug>.md
and the founder approves it before Plan writes 1 to 3 tasks.
"""

from __future__ import annotations

import re

from phases.common import PhaseError, PhaseResult, as_list, call, json_from

REQUIRED = ("title", "story", "acceptance_criteria")
SCHEMA = """{
  "title": "short feature name",
  "story": {"as_a": "type of user", "i_want": "what they do", "so_that": "why"},
  "acceptance_criteria": ["observable result a tester can check in a browser"],
  "out_of_scope": ["thing we will not build now"],
  "notes": "anything the planner must know, such as which existing page to extend"
}"""


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    return slug[:40].strip("-") or "feature"


def feature_path(number: int, title: str) -> str:
    return f"docs/features/{number}-{slugify(title)}.md"


def render(feature: dict, criteria: list[str], number: int) -> str:
    story = feature.get("story") if isinstance(feature.get("story"), dict) else {}
    parts = []
    for key, label in (("as_a", "As a"), ("i_want", "I want"), ("so_that", "so that")):
        if str(story.get(key, "")).strip():
            parts.append(f"**{label}** {str(story[key]).strip()}")
    lines = [
        f"# Feature: {str(feature.get('title', 'Feature')).strip()}",
        "",
        f"_Written by the Feature swarm (Swarms `SequentialWorkflow`: Product Owner, then MVP Cutter) for issue #{number}._",
        "",
        "## Story",
        "",
        ", ".join(parts) + "." if parts else "Not stated.",
        "",
        "## Acceptance criteria",
    ]
    lines += [f"- [ ] {c}" for c in criteria]
    for title, key in (("Out of scope", "out_of_scope"),):
        items = as_list(feature.get(key))
        lines += ["", f"## {title}"] + ([f"- {i}" for i in items] or ["- None"])
    notes = str(feature.get("notes", "")).strip()
    if notes:
        lines += ["", "## Notes for the planner", "", notes]
    return "\n".join(lines) + "\n"


def run(
    context: str,
    prd: str,
    design: str,
    number: int,
    feedback: str | None = None,
    previous: str | None = None,
    previous_path: str | None = None,
) -> PhaseResult:
    if not prd.strip():
        raise PhaseError("this project has no PRD yet (docs/PRD.md), so there is nothing to add a feature to")

    task = (
        "A founder wants a new feature in a product that already exists. The Product Owner writes one user "
        "story with acceptance criteria; the MVP Cutter trims it and gives the final answer, ending with "
        "one fenced json block that matches this schema:\n" + SCHEMA + "\n\n"
        "Rules: one story; 3 to 4 acceptance criteria that a tester can check on the public Vercel preview "
        "in a browser; small enough for 1 to 3 pull requests; reuse the existing pages and data; no new "
        "services; never write secret values.\n\n"
        "THE FOUNDER'S REQUEST:\n" + context[:3000] + "\n\nTHE PRODUCT'S PRD:\n" + prd[-5000:]
        + "\n\nTHE PRODUCT'S DESIGN:\n" + (design or "(none)")[-5000:]
    )
    if previous:
        task += "\n\nTHE PREVIOUS STORY (revise it, do not start over):\n" + previous[-3000:]
    if feedback:
        task += "\n\nTHE FOUNDER'S FEEDBACK (apply it):\n" + feedback

    response = call("feature", task, "feature-story")
    feature = json_from(
        response, REQUIRED, SCHEMA, roles=["MVP Cutter"], any_role_fallback=True, label="formatter-feature"
    )
    criteria = as_list(feature.get("acceptance_criteria"))
    if not criteria:
        raise PhaseError("the story has no acceptance criteria")
    title = str(feature.get("title", "Feature")).strip() or "Feature"
    path = previous_path or feature_path(number, title)

    story = feature.get("story") if isinstance(feature.get("story"), dict) else {}
    lines = [
        "Feature story ready from the Feature swarm (Swarms `SequentialWorkflow`: Product Owner, then MVP Cutter).",
        "",
        f"**{title}**: **As a** {story.get('as_a', '')}, **I want** {story.get('i_want', '')}, "
        f"**so that** {story.get('so_that', '')}.",
        "",
        "**Acceptance criteria**",
    ] + [f"- {c}" for c in criteria]
    out = as_list(feature.get("out_of_scope"))
    if out:
        lines += ["", "**Left out**"] + [f"- {o}" for o in out]
    lines += [
        "",
        'Reply "Go" to Project Lead to approve the story (it posts `/approve`), or say what to change '
        "(it posts `/revise`).",
    ]
    revised = " (revised)" if feedback else ""
    return PhaseResult(
        comment="\n".join(lines),
        files={path: render(feature, criteria, number)},
        commit_message=f"Feature story for issue #{number}{revised}",
        phase="story",
        status="waiting-approval",
        add_labels=["feature"],
        notify_summary=f"Feature story ready{revised}: {title}, {len(criteria)} acceptance criteria.",
        notify_question="Approve this feature story? Reply Go, or tell me what to change.",
    )

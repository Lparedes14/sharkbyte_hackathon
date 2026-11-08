"""Idea Lab (/score): four agents score an idea in parallel (Swarms ConcurrentWorkflow)."""

from __future__ import annotations

from statistics import mean

from phases.common import PhaseError, PhaseResult, as_list, call, cell, json_from

AGENTS = ("Idea Scout", "Market Researcher", "Feasibility Analyst", "MVP Cutter")
REQUIRED = ("score", "summary")
SCHEMA = (
    '{"score": <integer 1-10>, "summary": "<one sentence>", '
    '"points": ["<short point>"], "open_questions": ["<question for the founder>"]}'
)


def _score(value) -> int | None:
    try:
        return max(1, min(10, round(float(value))))
    except (TypeError, ValueError):
        return None


def run(context: str, feedback: str | None = None) -> PhaseResult:
    task = (
        "Evaluate this product idea for a small MVP that one developer can build in about "
        "8 hours with AI coding agents.\n\nIDEA:\n" + context
    )
    if feedback:
        task += "\n\nTHE FOUNDER'S ANSWERS AND FEEDBACK (take them into account):\n" + feedback

    response = call("idea_lab", task, "idea-lab")

    cards = []
    for name in AGENTS:
        try:
            obj = json_from(response, REQUIRED, SCHEMA, roles=[name], label=f"formatter-{name}")
        except PhaseError:
            cards.append({"name": name, "score": None, "summary": "(no usable answer)", "points": [], "questions": []})
            continue
        cards.append(
            {
                "name": name,
                "score": _score(obj.get("score")),
                "summary": str(obj.get("summary", "")).strip(),
                "points": as_list(obj.get("points"))[:4],
                "questions": as_list(obj.get("open_questions"))[:3],
            }
        )

    scores = [c["score"] for c in cards if c["score"] is not None]
    if not scores:
        raise PhaseError("no Idea Lab agent returned a usable score")
    overall = round(mean(scores), 1)

    questions: list[str] = []
    for card in cards:
        for q in card["questions"]:
            if q.lower() not in {x.lower() for x in questions}:
                questions.append(q)
    questions = questions[:6]

    lines = [
        "Idea Lab score card. Four agents scored this idea in parallel (Swarms `ConcurrentWorkflow`).",
        "",
        f"**Overall: {overall}/10**",
        "",
        "| Agent | Score | Summary |",
        "|---|---|---|",
    ]
    for card in cards:
        score = f"{card['score']}/10" if card["score"] is not None else "-"
        lines.append(f"| {card['name']} | {score} | {cell(card['summary'])} |")
    for card in cards:
        if card["points"]:
            lines += ["", f"**{card['name']}**"] + [f"- {p}" for p in card["points"]]
    if questions:
        lines += ["", "### Open questions"] + [f"{i}. {q}" for i, q in enumerate(questions, 1)]
    lines += [
        "",
        "Answer the questions through Project Lead (it posts them with `/revise`) to score the idea "
        "again, or tell Project Lead to build it.",
    ]

    return PhaseResult(
        comment="\n".join(lines),
        status="waiting-approval",
        add_labels=["idea"],
        notify_summary=(
            f"Idea scored {overall}/10 by the Idea Lab (4 agents in parallel). "
            f"{len(questions)} open questions."
        ),
        notify_question="Answer the open questions, or tell me to build it.",
    )

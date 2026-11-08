"""Phase and status labels on issues (PLAN.md section 8). The labels are the state."""

from __future__ import annotations

import github_io

# name -> (color, description)
LABELS = {
    "idea": ("1d76db", "Idea Inbox item"),
    "built": ("0e8a16", "This idea has its own project repo"),
    "phase:discovery": ("5319e7", "Deep Dive: writing the PRD"),
    "phase:design": ("5319e7", "Design: architecture and scope"),
    "phase:plan": ("5319e7", "Plan: tasks for Cursor"),
    "phase:build": ("5319e7", "Build: Cursor agents at work"),
    "phase:story": ("5319e7", "Feature story"),
    "phase:done": ("0e8a16", "Finished"),
    "status:running": ("fbca04", "An agent run is in progress"),
    "status:waiting-approval": ("d93f0b", "Waiting for your approval"),
    "status:waiting-go": ("d93f0b", "Waiting for your final Go"),
    "status:blocked": ("b60205", "A run failed; see the last comment"),
}


def names(issue: dict) -> set[str]:
    return {label["name"] for label in issue.get("labels", []) if isinstance(label, dict)}


def phase(labels: set[str]) -> str | None:
    for label in labels:
        if label.startswith("phase:"):
            return label.split(":", 1)[1]
    return None


def status(labels: set[str]) -> str | None:
    for label in labels:
        if label.startswith("status:"):
            return label.split(":", 1)[1]
    return None


def add(repo: str, number: int, labels: set[str], name: str) -> None:
    """Add one label (creating it with our color first) and keep the local set in sync."""
    if name in labels:
        return
    color, description = LABELS.get(name, ("ededed", ""))
    github_io.ensure_label(repo, name, color, description)
    github_io.add_labels(repo, number, [name])
    labels.add(name)


def _replace(repo: str, number: int, labels: set[str], prefix: str, value: str | None) -> None:
    wanted = f"{prefix}:{value}" if value else None
    for label in [x for x in labels if x.startswith(prefix + ":") and x != wanted]:
        github_io.remove_label(repo, number, label)
        labels.discard(label)
    if wanted:
        add(repo, number, labels, wanted)


def set_phase(repo: str, number: int, labels: set[str], value: str | None) -> None:
    _replace(repo, number, labels, "phase", value)


def set_status(repo: str, number: int, labels: set[str], value: str | None) -> None:
    _replace(repo, number, labels, "status", value)

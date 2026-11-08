"""Shared pieces for phases: the result type, Swarms calls with raw-output logging, JSON repair."""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path

import parsing
import swarms_client


class PhaseError(Exception):
    """A phase could not finish. The message is safe to post on GitHub."""


@dataclass
class PhaseResult:
    comment: str
    files: dict[str, str] = field(default_factory=dict)
    commit_message: str = ""
    phase: str | None = None
    status: str | None = None
    add_labels: list[str] = field(default_factory=list)
    notify_event: str = "approval_needed"
    notify_summary: str = ""
    notify_question: str = ""


def save_raw(label: str, data: dict) -> None:
    """Keep every raw Swarms response; the workflow uploads the folder as an artifact."""
    folder = Path(os.environ.get("ARTIFACT_DIR", ".orchestrator-runs"))
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{time.strftime('%Y%m%d-%H%M%S')}-{re.sub(r'[^a-z0-9-]+', '-', label.lower())}.json"
    (folder / name).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def call(spec_name: str, task: str, label: str | None = None) -> dict:
    response = swarms_client.run_swarm(swarms_client.load_spec(spec_name), task)
    save_raw(label or spec_name, response)
    return response


def json_from(
    response: dict,
    required: tuple,
    schema_text: str,
    roles: list[str] | None = None,
    any_role_fallback: bool = False,
    label: str = "formatter",
) -> dict:
    """The JSON a phase needs. If the agents' own JSON is missing or broken, ask the Formatter once."""
    obj = parsing.find_json(response, roles=roles, required=required)
    if obj is None and roles and any_role_fallback:
        obj = parsing.find_json(response, required=required)
    if obj is not None:
        return obj

    text = parsing.joined_outputs(response, None if any_role_fallback else roles)[-15000:]
    if not text.strip():
        raise PhaseError("the agents returned no text")
    task = (
        "Convert the text below into one JSON object that matches this schema. "
        "Use only information from the text.\n\nSCHEMA:\n"
        + schema_text
        + "\n\nTEXT:\n"
        + text
    )
    fixed = call("formatter", task, label)
    obj = parsing.find_json(fixed, required=required)
    if obj is None:
        raise PhaseError("the agents did not return the expected JSON, even after the Formatter")
    return obj


def as_list(value) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    return [str(item).strip() for item in items if str(item).strip()]


def cell(text: str) -> str:
    """Safe text for one Markdown table cell."""
    return str(text).replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip()

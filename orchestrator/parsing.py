"""Pull JSON out of agent output (PLAN.md section 6, output contract).

Every phase asks its agents to end with a fenced ```json block. The Swarms API returns
"output": [{"role": "<agent name>", "content": "<text>"}, ...]. HierarchicalSwarm also adds
"System" and "Director" entries, which are skipped here.
"""

from __future__ import annotations

import json
import re

FENCE = re.compile(r"```[ \t]*(?:json)?[ \t]*\r?\n?(.*?)```", re.DOTALL | re.IGNORECASE)
SKIP_ROLES = {"System", "Director"}


def json_blocks(text: str) -> list:
    """Every fenced block in the text that parses as JSON, in order."""
    found = []
    for match in FENCE.finditer(text or ""):
        try:
            found.append(json.loads(match.group(1).strip()))
        except ValueError:
            continue
    if not found:
        stripped = (text or "").strip()
        if stripped.startswith("{"):
            try:
                found.append(json.loads(stripped))
            except ValueError:
                pass
    return found


def outputs(response: dict) -> list[tuple[str, str]]:
    """(role, text) for each agent answer, without the System and Director entries."""
    result = []
    for item in (response or {}).get("output") or []:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "")
        if role in SKIP_ROLES:
            continue
        content = item.get("content")
        result.append((role, content if isinstance(content, str) else json.dumps(content)))
    return result


def find_json(response: dict, roles: list[str] | None = None, required: tuple = ()) -> dict | None:
    """The last JSON object with all required keys, searching the latest answers first."""
    for role, content in reversed(outputs(response)):
        if roles and role not in roles:
            continue
        for obj in reversed(json_blocks(content)):
            if isinstance(obj, dict) and all(key in obj for key in required):
                return obj
    return None


def joined_outputs(response: dict, roles: list[str] | None = None) -> str:
    """All agent answers as one text, for the Formatter fallback."""
    return "\n\n".join(
        f"[{role}]\n{content}" for role, content in outputs(response) if not roles or role in roles
    )

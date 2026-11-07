"""S1b: try HierarchicalSwarm, GroupChat, MajorityVoting with the S1 request shape."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
URL = "https://api.swarms.world/v1/swarm/completions"
MODEL = "openrouter/x-ai/grok-4.3"

SWARM_TYPES = ("HierarchicalSwarm", "GroupChat", "MajorityVoting")


def agent(name: str, description: str, system_prompt: str) -> dict:
    """Same agent fields as tests/s1_request.json — nothing extra."""
    return {
        "agent_name": name,
        "description": description,
        "system_prompt": system_prompt,
        "model_name": MODEL,
        "max_loops": 1,
    }


def body_for(swarm_type: str) -> dict:
    """Reuse S1 top-level shape: name, swarm_type, task, agents."""
    if swarm_type == "HierarchicalSwarm":
        agents = [
            agent(
                "Lead",
                "Directs the tiny team",
                "You are Lead. In one short sentence, assign the task and give a final answer.",
            ),
            agent(
                "Worker",
                "Follows the lead",
                "You are Worker. In one short sentence, do what Lead asked.",
            ),
        ]
        task = "Pick a one-word team color and confirm it."
    elif swarm_type == "GroupChat":
        agents = [
            agent(
                "Alice",
                "Chat participant A",
                "You are Alice. Reply in one short sentence in this group chat.",
            ),
            agent(
                "Bob",
                "Chat participant B",
                "You are Bob. Reply in one short sentence in this group chat.",
            ),
            agent(
                "Carol",
                "Chat participant C",
                "You are Carol. Reply in one short sentence summarizing the chat.",
            ),
        ]
        task = "Agree on a one-word snack for the team."
    else:  # MajorityVoting
        agents = [
            agent(
                "VoterA",
                "Votes yes or no",
                "You are VoterA. Vote YES or NO in one short sentence with a reason.",
            ),
            agent(
                "VoterB",
                "Votes yes or no",
                "You are VoterB. Vote YES or NO in one short sentence with a reason.",
            ),
            agent(
                "VoterC",
                "Votes yes or no",
                "You are VoterC. Vote YES or NO in one short sentence with a reason.",
            ),
        ]
        task = "Should we ship the hello-world demo today? Vote YES or NO."

    return {
        "name": f"s1b-{swarm_type.lower()}",
        "swarm_type": swarm_type,
        "task": task,
        "agents": agents,
    }


def preview_output(data: object) -> str:
    if not isinstance(data, dict):
        text = str(data)
        return text[:160] + ("…" if len(text) > 160 else "")

    output = data.get("output")
    if isinstance(output, list) and output:
        parts = []
        for item in output[:3]:
            if isinstance(item, dict):
                role = item.get("role") or item.get("agent_name") or "?"
                content = str(item.get("content") or "")
                snippet = content.replace("\n", " ")[:80]
                parts.append(f"{role}: {snippet}")
            else:
                parts.append(str(item)[:80])
        return " | ".join(parts)

    for key in ("result", "response", "message", "detail", "status"):
        if key in data and data[key] is not None:
            text = str(data[key]).replace("\n", " ")
            return text[:160] + ("…" if len(text) > 160 else "")

    text = json.dumps(data, ensure_ascii=False)
    return text[:160] + ("…" if len(text) > 160 else "")


def note_for(status_code: int, data: object, raw: str) -> str:
    if status_code == 200:
        if isinstance(data, dict) and data.get("status") == "success":
            n = data.get("number_of_agents")
            return f"ok; agents={n}" if n is not None else "ok"
        return "HTTP 200 but unexpected body"
    detail = ""
    if isinstance(data, dict) and "detail" in data:
        detail = str(data["detail"]).replace("\n", " ")
    else:
        detail = raw.replace("\n", " ")
    return (detail[:120] + "…") if len(detail) > 120 else detail


def main() -> None:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("SWARMS_API_KEY")
    if not api_key:
        print("SWARMS_API_KEY missing from .env")
        sys.exit(1)

    # Confirm we start from the proven S1 shape (task + agent fields).
    s1 = json.loads((TESTS / "s1_request.json").read_text(encoding="utf-8"))
    assert "task" in s1 and "agents" in s1 and "swarm_type" in s1

    rows: list[tuple[str, int, str]] = []

    for swarm_type in SWARM_TYPES:
        body = body_for(swarm_type)
        print(f"\n=== {swarm_type} ===")
        try:
            resp = requests.post(
                URL,
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json=body,
                timeout=300,
            )
        except requests.RequestException as exc:
            print(f"HTTP error: {exc}")
            rows.append((swarm_type, 0, str(exc)[:120]))
            continue

        print(f"HTTP {resp.status_code}")
        raw = resp.text
        try:
            data = resp.json()
        except ValueError:
            data = None

        if resp.status_code != 200:
            print(raw)
            rows.append((swarm_type, resp.status_code, note_for(resp.status_code, data, raw)))
            continue

        preview = preview_output(data if data is not None else raw)
        print(f"preview: {preview}")
        rows.append((swarm_type, resp.status_code, note_for(resp.status_code, data, raw)))

    print("\n=== Summary ===")
    print(f"{'swarm_type':<22} {'status':<8} note")
    print("-" * 72)
    for swarm_type, status, note in rows:
        print(f"{swarm_type:<22} {status:<8} {note}")


if __name__ == "__main__":
    main()

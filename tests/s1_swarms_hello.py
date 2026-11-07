"""S1: Swarms hello world — SequentialWorkflow with 2 tiny agents."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

ROOT = Path(__file__).resolve().parents[1]
TESTS = Path(__file__).resolve().parent
URL = "https://api.swarms.world/v1/swarm/completions"
PRIMARY_MODEL = "grok-4"


def build_body(model_name: str) -> dict:
    return {
        "name": "s1-hello",
        "swarm_type": "SequentialWorkflow",
        # Required by API: "no task or tasks or messages provided"
        "task": "Each agent should introduce itself in one short sentence.",
        "agents": [
            {
                "agent_name": "Greeter",
                "description": "Says hello briefly",
                "system_prompt": (
                    "You are Greeter. Reply in one short sentence that clearly "
                    "includes the word HELLO_FROM_GREETER."
                ),
                "model_name": model_name,
                "max_loops": 1,
            },
            {
                "agent_name": "Responder",
                "description": "Acknowledges the greeter",
                "system_prompt": (
                    "You are Responder. Reply in one short sentence that clearly "
                    "includes the word HELLO_FROM_RESPONDER."
                ),
                "model_name": model_name,
                "max_loops": 1,
            },
        ],
    }


def pick_from_available(api_key: str, models_url: str) -> str | None:
    """Fetch the models URL named in the error and pick one Grok-like model."""
    r = requests.get(
        models_url,
        headers={"x-api-key": api_key},
        timeout=60,
    )
    print(f"Fetched {models_url} -> HTTP {r.status_code}")
    if r.status_code != 200:
        print(r.text)
        return None
    try:
        payload = r.json()
    except ValueError:
        print(r.text)
        return None
    names = [
        m.get("model_name")
        for m in (payload.get("models") or [])
        if isinstance(m, dict) and m.get("model_name")
    ]
    # Prefer Grok via routes Swarms can auth; then cheap OpenAI defaults from docs.
    preferred = [
        "openrouter/x-ai/grok-4.3",
        "openrouter/x-ai/grok-4.6",
        "openrouter/x-ai/grok-4.20",
        "gpt-4o-mini",
        "gpt-4.1-mini",
        "claude-sonnet-5",
    ]
    for name in preferred:
        if name in names:
            return name
    return names[0] if names else None


def extract_valid_model(error_text: str, api_key: str) -> str | None:
    """Pick one model name from an API error that lists valid options."""
    url_match = re.search(r"https://api\.swarms\.world/v1/models/available", error_text)
    if url_match:
        return pick_from_available(api_key, url_match.group(0))

    listed = re.findall(
        r"['\"`]([a-zA-Z0-9._:/-]+)['\"`]",
        error_text,
    )
    for name in listed:
        if name.lower() in {"grok-4", "model", "model_name", "models"}:
            continue
        if any(ch.isdigit() for ch in name) or "-" in name or "/" in name:
            return name
    m = re.search(
        r"(?:valid|available|supported|allowed)\s+models?\s*[:\-]\s*(.+)",
        error_text,
        re.IGNORECASE | re.DOTALL,
    )
    if m:
        chunk = m.group(1).split("\n")[0]
        parts = re.split(r"[,;\s]+", chunk.strip(" .[](){}"))
        for part in parts:
            part = part.strip(" '\"`")
            if part and part.lower() != "grok-4" and len(part) > 2:
                return part
    return None


def assert_no_key(payload: object, api_key: str, label: str) -> None:
    blob = json.dumps(payload, ensure_ascii=False)
    if api_key and api_key in blob:
        print(f"Refusing to save {label}: API key appears in the payload.")
        sys.exit(1)


def post(api_key: str, body: dict) -> requests.Response:
    return requests.post(
        URL,
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json",
        },
        json=body,
        timeout=180,
    )


def main() -> None:
    load_dotenv(ROOT / ".env")
    api_key = os.getenv("SWARMS_API_KEY")
    if not api_key:
        print("SWARMS_API_KEY missing from .env")
        sys.exit(1)

    model = PRIMARY_MODEL
    body = build_body(model)
    print(f"Trying model_name={model!r} ...")
    resp = post(api_key, body)

    if resp.status_code != 200:
        print(f"HTTP {resp.status_code}")
        print(resp.text)
        # Only retry model if this looks like a model rejection
        alt = extract_valid_model(resp.text, api_key)
        if not alt:
            print("Request failed; stopping (no alternate model parsed from error).")
            sys.exit(1)
        print(f"\nAPI rejected {model!r}. Trying listed model {alt!r} ...")
        model = alt
        body = build_body(model)
        resp = post(api_key, body)

    print(f"HTTP {resp.status_code}")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except ValueError:
        print(resp.text)
        print("Response was not JSON; stopping.")
        sys.exit(1)

    if resp.status_code != 200:
        print("Request failed; stopping.")
        sys.exit(1)

    assert_no_key(body, api_key, "tests/s1_request.json")
    assert_no_key(data, api_key, "tests/s1_response.json")

    (TESTS / "s1_request.json").write_text(
        json.dumps(body, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (TESTS / "s1_response.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"\nSaved working request to {TESTS / 's1_request.json'}")
    print(f"Saved response to {TESTS / 's1_response.json'}")
    print(f"Working model_name: {model}")


if __name__ == "__main__":
    main()

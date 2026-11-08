"""Thin wrapper over the Swarms HTTP API. Raw requests, no SDK (see PLAN.md section 7)."""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path

import requests

BASE_URL = "https://api.swarms.world"
COMPLETIONS_PATH = "/v1/swarm/completions"
DEFAULT_TIMEOUT = 600  # seconds; real phases can take a while
RETRIES = 2  # extra attempts, on network errors and quick temporary server errors
TRANSIENT_STATUSES = (502, 503, 504)
# The API gateway answers 503 when a call runs longer than about 30 seconds, but the swarm keeps
# running. Retrying would run (and bill) it again, so a slow 503 is recovered from the logs instead.
GATEWAY_LIMIT_SECONDS = 25
LOGS_PATH = "/v1/account/logs"
POLL_SECONDS = 10
AGENTS_DIR = Path(__file__).resolve().parent / "agents"
SPEC_KEYS = ("name", "description", "swarm_type", "agents")


class SwarmsError(Exception):
    """Raised for a failed Swarms call. The message never contains the key or response body."""


def default_model() -> str:
    """One config value for the model name, so it is easy to switch.

    grok-4 is a 404 (S1). grok-4.3 is too slow: a 4-agent call passes the gateway's ~30 second
    limit and gets a 503. openrouter/x-ai/grok-4.20 finished the Idea Lab in about 10 seconds.
    """
    return os.environ.get("SWARMS_MODEL", "").strip() or "openrouter/x-ai/grok-4.20"


def load_spec(name: str) -> dict:
    """Read orchestrator/agents/<name>.json and fill in the model and loop count."""
    raw = json.loads((AGENTS_DIR / f"{name}.json").read_text(encoding="utf-8"))
    spec = {key: raw[key] for key in SPEC_KEYS if key in raw}
    model = default_model()
    spec["agents"] = [
        {"model_name": model, "max_loops": 1, **agent} for agent in raw.get("agents", [])
    ]
    return spec


def run_swarm(spec: dict, task: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """POST one swarm spec plus a top-level task (required by the API, S1) and return the JSON."""
    api_key = os.environ.get("SWARMS_API_KEY", "").strip()
    if not api_key:
        raise SwarmsError("SWARMS_API_KEY is not set")

    # A unique swarm name lets us find this exact job in the account logs after a gateway timeout.
    name = f"{spec.get('name', 'swarm')}-{uuid.uuid4().hex[:8]}"
    body = {**spec, "name": name, "task": task}
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    last_error = "unknown error"
    for attempt in range(RETRIES + 1):
        started = time.monotonic()
        try:
            resp = requests.post(
                BASE_URL + COMPLETIONS_PATH, headers=headers, json=body, timeout=timeout
            )
        except (requests.ConnectionError, requests.Timeout) as exc:
            last_error = f"network error ({type(exc).__name__})"
            time.sleep(2 * (attempt + 1))
            continue
        except requests.RequestException as exc:
            raise SwarmsError(f"request failed ({type(exc).__name__})") from None

        elapsed = time.monotonic() - started
        if resp.status_code == 503 and elapsed >= GATEWAY_LIMIT_SECONDS:
            # The gateway gave up, but the swarm keeps running. Wait for it and fetch its result.
            print(f"Swarms gateway timed out after {elapsed:.0f}s; waiting for job '{name}' to finish")
            recovered = _recover(name, headers, started + timeout)
            if recovered is not None:
                return recovered
            raise SwarmsError(
                f"the swarm ran past the Swarms gateway limit (about 30 seconds) and its result "
                f"did not appear within {timeout} seconds"
            )
        if resp.status_code in TRANSIENT_STATUSES and attempt < RETRIES:
            last_error = f"HTTP {resp.status_code}"
            time.sleep(10 * (attempt + 1))
            continue
        if not resp.ok:
            raise SwarmsError(f"HTTP {resp.status_code}")
        try:
            return resp.json()
        except ValueError:
            raise SwarmsError("response was not JSON") from None

    raise SwarmsError(last_error)


def _recover(name: str, headers: dict, deadline: float) -> dict | None:
    """Poll the account logs for the job with this swarm name, then fetch its stored result.

    Non-streaming jobs keep their full output, so GET /v1/job/{job_id} returns the same
    shape as a normal completion. The log entry appears when the job finishes.
    """
    while time.monotonic() < deadline:
        time.sleep(POLL_SECONDS)
        try:
            logs = requests.get(BASE_URL + LOGS_PATH, headers=headers, timeout=60).json().get("logs") or []
        except (requests.RequestException, ValueError, AttributeError):
            continue
        for entry in logs:
            data = (entry or {}).get("data") or {}
            if data.get("swarm_name") != name or not data.get("job_id"):
                continue
            if data.get("status") not in (None, "success"):
                raise SwarmsError(f"the swarm finished with status '{data.get('status')}'")
            try:
                job = requests.get(f"{BASE_URL}/v1/job/{data['job_id']}", headers=headers, timeout=60)
                result = job.json() if job.ok else {}
            except (requests.RequestException, ValueError):
                result = {}
            if isinstance(result.get("output"), list):
                return result
    return None

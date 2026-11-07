"""Thin wrapper over the Swarms HTTP API. Raw requests, no SDK (see PLAN.md section 7)."""

from __future__ import annotations

import os
import time

import requests

BASE_URL = "https://api.swarms.world"
COMPLETIONS_PATH = "/v1/swarm/completions"
DEFAULT_TIMEOUT = 600  # seconds; real phases can take a while
RETRIES = 2  # extra attempts, on network errors only


class SwarmsError(Exception):
    """Raised for a failed Swarms call. The message never contains the key or response body."""


def default_model() -> str:
    """One config value for the model name, so it is easy to switch (S1: grok-4 is a 404)."""
    return os.environ.get("SWARMS_MODEL", "").strip() or "openrouter/x-ai/grok-4.3"


def run_swarm(spec: dict, task: str, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """POST one swarm spec plus a top-level task (required by the API, S1) and return the JSON."""
    api_key = os.environ.get("SWARMS_API_KEY", "").strip()
    if not api_key:
        raise SwarmsError("SWARMS_API_KEY is not set")

    body = {**spec, "task": task}
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    last_error = "unknown error"
    for attempt in range(RETRIES + 1):
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

        if not resp.ok:
            raise SwarmsError(f"HTTP {resp.status_code}")
        try:
            return resp.json()
        except ValueError:
            raise SwarmsError("response was not JSON") from None

    raise SwarmsError(last_error)

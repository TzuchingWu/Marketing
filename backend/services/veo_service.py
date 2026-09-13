"""
Google Veo video generation, via the Gemini API's long-running-operation
endpoints (simple API-key auth -- NOT Vertex AI's OAuth/service-account
path, which would be a much heavier setup for a single-account project
like this one).

This is fundamentally different from every other integration in this
app: it's an async job, not a synchronous request/response. Submitting
returns an operation name; we then poll it until Google reports the job
done (or it times out). Real per-clip cost, no free tier, generation
typically takes anywhere from ~30 seconds to a few minutes.

Degrades to a clear status dict on any failure -- missing key, bad
auth, quota, timeout -- never raises. Callers (the MCP tool) should
treat "the video didn't generate" as a normal, expected outcome, not an
error condition -- the ad *concept* (built in marketing_service.py) is
still useful on its own even when the actual clip can't be produced.
"""

from __future__ import annotations

import os
import time
from typing import Optional

import httpx

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
_MODEL = os.getenv("VEO_MODEL", "veo-3.1-fast-generate-preview")
_REQUEST_TIMEOUT = 20.0
_POLL_INTERVAL_SECONDS = 5.0
_MAX_WAIT_SECONDS = 180.0  # give up after ~3 minutes rather than hang a request indefinitely


def is_configured() -> bool:
    return bool(os.getenv("GOOGLE_VEO_API_KEY"))


def generate_video(prompt: str, aspect_ratio: str = "9:16", duration_seconds: int = 8) -> dict:
    """Submit a Veo generation job for `prompt` and poll until it
    completes or we give up.

    Returns:
        {"status": "not_configured" | "ready" | "failed" | "timed_out",
         "video_url": str | None, "reason": str | None}
    """
    if not is_configured():
        return {"status": "not_configured", "video_url": None, "reason": "GOOGLE_VEO_API_KEY not set"}

    key = os.getenv("GOOGLE_VEO_API_KEY")

    operation_name, submit_error = _submit(prompt, aspect_ratio, duration_seconds, key)
    if submit_error:
        return {"status": "failed", "video_url": None, "reason": submit_error}

    return _poll_until_done(operation_name, key)


def _submit(prompt: str, aspect_ratio: str, duration_seconds: int, key: str) -> tuple[Optional[str], Optional[str]]:
    try:
        response = httpx.post(
            f"{_BASE_URL}/models/{_MODEL}:predictLongRunning",
            params={"key": key},
            json={
                "instances": [{"prompt": prompt}],
                "parameters": {"aspectRatio": aspect_ratio, "durationSeconds": duration_seconds},
            },
            timeout=_REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
    except httpx.HTTPStatusError as exc:
        return None, f"Veo submit rejected ({exc.response.status_code}): {exc.response.text[:300]}"
    except httpx.HTTPError as exc:
        return None, f"Veo submit request failed: {exc}"
    except ValueError:
        return None, "Veo submit returned a non-JSON response"

    operation_name = data.get("name")
    if not operation_name:
        return None, f"Veo submit response had no operation name: {data}"
    return operation_name, None


def _poll_until_done(operation_name: str, key: str) -> dict:
    deadline = time.monotonic() + _MAX_WAIT_SECONDS

    while time.monotonic() < deadline:
        time.sleep(_POLL_INTERVAL_SECONDS)
        try:
            response = httpx.get(f"{_BASE_URL}/{operation_name}", params={"key": key}, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except httpx.HTTPError as exc:
            return {"status": "failed", "video_url": None, "reason": f"Veo poll request failed: {exc}"}
        except ValueError:
            return {"status": "failed", "video_url": None, "reason": "Veo poll returned a non-JSON response"}

        if not data.get("done"):
            continue

        if "error" in data:
            return {"status": "failed", "video_url": None, "reason": str(data["error"])}

        samples = (data.get("response", {}) or {}).get("generateVideoResponse", {}).get("generatedSamples", [])
        if not samples:
            return {"status": "failed", "video_url": None, "reason": f"Veo finished with no video: {data}"}

        video_uri = samples[0].get("video", {}).get("uri")
        if not video_uri:
            return {"status": "failed", "video_url": None, "reason": f"Veo sample had no video URI: {samples[0]}"}

        return {"status": "ready", "video_url": f"{video_uri}&key={key}", "reason": None}

    return {"status": "timed_out", "video_url": None,
            "reason": f"Video did not finish generating within {int(_MAX_WAIT_SECONDS)}s"}

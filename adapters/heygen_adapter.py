"""
HeyGen adapter: render text to avatar + poll status, with dry-run support.

Standard-library only; requires an injected HTTP client in non-dry-run mode.
"""
from __future__ import annotations

from dataclasses import dataclass
import time
import io
import random
from typing import Any, Mapping, Protocol, runtime_checkable


@runtime_checkable
class HTTPClientProtocol(Protocol):
    def get(self, url: str, *, headers: Mapping[str, str] | None = None, params: Mapping[str, Any] | None = None) -> Mapping[str, Any]:
        ...

    def post(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        data: Mapping[str, Any] | None = None,
        json: Mapping[str, Any] | None = None,
        files: Mapping[str, Any] | None = None,
    ) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class HeyGenRenderRequest:
    script_text: str
    avatar_id: str
    voice_id: str | None = None
    background: str | None = None


class HeyGenAdapter:
    BASE_URL = "https://api.heygen.com/v2"

    def __init__(
        self,
        api_key: str | None,
        *,
        http_client: HTTPClientProtocol | None = None,
        dry_run: bool = False,
    ) -> None:
        self.api_key = api_key
        self.http_client = http_client
        self.dry_run = bool(dry_run)
        # Simple in-memory rate-limit guard: timestamp of last call
        self._last_call_ts: float | None = None

    def _headers(self) -> Mapping[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

    def _rate_limit_guard(self, min_interval_seconds: float = 0.25) -> None:
        """Ensure we don't call HeyGen too fast in live mode.

        This is a conservative client-side guard to avoid spikes. It's not a
        substitute for server-side rate limits but reduces burstiness.
        """
        if self.dry_run:
            return
        now = time.time()
        if self._last_call_ts is None:
            self._last_call_ts = now
            return
        elapsed = now - self._last_call_ts
        if elapsed < min_interval_seconds:
            sleep_for = min_interval_seconds - elapsed
            time.sleep(sleep_for)
        self._last_call_ts = time.time()

    def render_text_to_avatar(self, request: HeyGenRenderRequest) -> Mapping[str, Any]:
        if self.dry_run:
            return {
                "video_id": "dry-video-abc123",
                "script_preview": request.script_text[:40],
                "avatar_id": request.avatar_id,
            }
        if self.http_client is None:
            raise RuntimeError(
                "HeyGenAdapter requires an http_client in non-dry-run mode."
            )
        self._rate_limit_guard()
        # Retry with exponential backoff for transient errors (502/503/429)
        max_attempts = 4
        base_backoff = 0.5
        payload = {
            "script_text": request.script_text,
            "avatar_id": request.avatar_id,
        }
        if request.voice_id:
            payload["voice_id"] = request.voice_id
        if request.background:
            payload["background"] = request.background
        url = f"{self.BASE_URL}/videos/createByText"
        attempt = 0
        while True:
            attempt += 1
            try:
                res = self.http_client.post(url, headers=self._headers(), json=payload)
                return res
            except Exception as exc:  # pragma: no cover - network dependent
                # Basic pattern: for a few retriable attempts, sleep with backoff
                if attempt >= max_attempts:
                    raise
                backoff = base_backoff * (2 ** (attempt - 1)) + (random.random())
                time.sleep(backoff)
                continue

    def poll_status(self, video_id: str) -> Mapping[str, Any]:
        if self.dry_run:
            return {"video_id": video_id, "status": "completed(dry)", "progress": 100}
        if self.http_client is None:
            raise RuntimeError("poll_status requires http_client in non-dry-run mode")
        # Safe polling: capped attempts, jittered backoff to avoid hot loops
        self._rate_limit_guard(min_interval_seconds=0.5)
        url = f"{self.BASE_URL}/videos/{video_id}"
        attempts = 0
        max_attempts = 12
        base = 0.5
        res: dict[str, Any] = {}
        while attempts < max_attempts:
            attempts += 1
            rr = self.http_client.get(url, headers=self._headers())
            # normalize to a mutable dict for post-processing
            res = dict(rr) if isinstance(rr, Mapping) else (rr if isinstance(rr, dict) else {"result": rr})
            status = res.get("status") or res.get("state") or "unknown"
            # If HeyGen returns a download URL on completion, include it
            if status in {"completed", "ready", "done"} or str(status).lower().startswith("completed"):
                # Optionally fetch the file into a bytes buffer if a download_url exists
                dl = res.get("download_url") or res.get("result_url")
                if dl:
                    try:
                        content = self._download_file(dl)
                        res["download_bytes_len"] = len(content)
                    except Exception:
                        # Don't fail polling because of download issues; surface url
                        res["download_bytes_len"] = None
                return res
            # sleep with exponential backoff + small jitter
            backoff = base * (2 ** (attempts - 1))
            time.sleep(min(backoff, 10))
        # If we exhausted attempts, return last response with a sentinel
        res.setdefault("status", "unknown")
        res.setdefault("note", "poll_timeout")
        return res

    def _download_file(self, url: str, *, timeout_seconds: int = 30) -> bytes:
        """Download a file from a URL using the injected http_client.

        Returns bytes. In dry-run mode, returns empty bytes.
        """
        if self.dry_run:
            return b""
        if self.http_client is None:
            raise RuntimeError("_download_file requires http_client in non-dry-run mode")
        # We expect the http_client.get to accept a url and return binary content under 'content' or similar.
        # For compatibility, attempt to use a 'stream' or 'content' keys.
        res = self.http_client.get(url, headers=self._headers())
        if isinstance(res, dict) and res.get("content"):
            return res["content"]
        # Fallback: if http_client returns raw bytes (some clients might), return as-is
        if isinstance(res, (bytes, bytearray)):
            return bytes(res)
        # If nothing matched, attempt to fetch via a simple passthrough 'get' that returns a mapping with url
        # Not much else we can do without a real http client
        raise RuntimeError("Unexpected download result from http_client")

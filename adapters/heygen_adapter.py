"""
HeyGen adapter: render text to avatar + poll status, with dry-run support.

Standard-library only; requires an injected HTTP client in non-dry-run mode.
"""
from __future__ import annotations

from dataclasses import dataclass
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

    def _headers(self) -> Mapping[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}

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
        payload = {
            "script_text": request.script_text,
            "avatar_id": request.avatar_id,
        }
        if request.voice_id:
            payload["voice_id"] = request.voice_id
        if request.background:
            payload["background"] = request.background
        url = f"{self.BASE_URL}/videos/createByText"
        return self.http_client.post(url, headers=self._headers(), json=payload)

    def poll_status(self, video_id: str) -> Mapping[str, Any]:
        if self.dry_run:
            return {"video_id": video_id, "status": "completed(dry)", "progress": 100}
        if self.http_client is None:
            raise RuntimeError("poll_status requires http_client in non-dry-run mode")
        url = f"{self.BASE_URL}/videos/{video_id}"
        return self.http_client.get(url, headers=self._headers())

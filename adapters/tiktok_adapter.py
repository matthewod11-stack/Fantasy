"""
TikTok adapter (OAuth + video upload) with dry-run support.

Standard-library only; callers must inject an HTTP client implementing a small
Protocol with get/post methods.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable
from urllib.parse import urlencode
from packages.utils.logging import get_logger

_log = get_logger("adapters.tiktok")


def _banner_if_live(dry_run: bool, cfg: "TikTokOAuthConfig") -> None:
    """Emit a conspicuous log/banner when running in live mode.

    This helps ops notice production-impacting runs in logs.
    """
    if not dry_run:
        try:
            key = cfg.client_key
        except Exception:
            key = None
        _log.info("TIKTOK LIVE MODE ENABLED", extra={"data": {"client_key": key}})


@runtime_checkable
class HTTPClientProtocol(Protocol):
    """Minimal HTTP client protocol used by adapters."""

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
class TikTokOAuthConfig:
    client_key: str
    client_secret: str
    redirect_uri: str


@dataclass(frozen=True)
class TikTokOAuthTokens:
    access_token: str
    refresh_token: str
    open_id: str
    expires_in: int


class TikTokAdapter:
    """TikTok OAuth + upload operations with injectable HTTP client.

    In dry-run mode, returns deterministic stubs without network calls.
    """

    BASE_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
    TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
    INIT_UPLOAD_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
    UPLOAD_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/upload/"
    CHECK_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/query/"
    LIST_URL = "https://open.tiktokapis.com/v2/post/publish/list/"

    def __init__(
        self,
        config: TikTokOAuthConfig,
        *,
        http_client: HTTPClientProtocol | None = None,
        dry_run: bool = False,
    ) -> None:
        self.config = config
        self.oauth_config = config
        self.http_client = http_client
        self.dry_run = bool(dry_run)
        # Fail fast if live and required creds are missing
        if not self.dry_run:
            if not self.config.client_key or not self.config.client_secret:
                raise RuntimeError("TikTokAdapter: missing client_key/client_secret in live mode")
        # Emit a banner when running live to make runs noisy in logs
        _banner_if_live(self.dry_run, self.config)

    # OAuth
    def build_login_url(self, state: str, scopes: list[str]) -> str:
        params = {
            "client_key": self.config.client_key,
            "response_type": "code",
            "scope": " ".join(scopes),
            "redirect_uri": self.config.redirect_uri,
            "state": state,
        }
        return f"{self.BASE_AUTH_URL}?{urlencode(params)}"

    def exchange_code(self, code: str) -> TikTokOAuthTokens:
        if self.dry_run:
            return TikTokOAuthTokens(
                access_token=f"dry_access_{code[:6]}",
                refresh_token=f"dry_refresh_{code[:6]}",
                open_id=f"dry_open_{code[:6]}",
                expires_in=3600,
            )

        if self.http_client is None:
            raise RuntimeError(
                "TikTokAdapter requires an http_client in non-dry-run mode. "
                "Provide a client implementing HTTPClientProtocol."
            )
        payload = {
            "client_key": self.config.client_key,
            "client_secret": self.config.client_secret,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.config.redirect_uri,
        }
        result = self.http_client.post(self.TOKEN_URL, data=payload)
        _log.info("oauth.exchange", extra={"data": {"client_key": self.config.client_key, "open_id": result.get("open_id")}})
        try:
            return TikTokOAuthTokens(
                access_token=result["access_token"],
                refresh_token=result["refresh_token"],
                open_id=result["open_id"],
                expires_in=int(result["expires_in"]),
            )
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"Unexpected token response: {result}") from exc

    # Upload flow
    def init_upload(self, access_token: str, open_id: str, *, draft: bool = True) -> Mapping[str, Any]:
        if self.dry_run:
            return {"upload_id": "dry-upload-123", "draft": draft, "open_id": open_id}
        if self.http_client is None:
            raise RuntimeError("init_upload requires http_client in non-dry-run mode")
        headers = {"Authorization": f"Bearer {access_token}"}
        data = {"open_id": open_id, "draft": draft}
        res = self.http_client.post(self.INIT_UPLOAD_URL, headers=headers, json=data)
        _log.info("upload.init", extra={"data": {"open_id": open_id, "Authorization": headers.get("Authorization")}})
        return res

    def upload_video(
        self,
        access_token: str,
        open_id: str,
        upload_id: str,
        video_bytes: bytes,
        *,
        filename: str = "draft.mp4",
    ) -> Mapping[str, Any]:
        if self.dry_run:
            return {
                "upload_id": upload_id,
                "size": len(video_bytes),
                "filename": filename,
                "status": "uploaded(dry)",
            }
        if self.http_client is None:
            raise RuntimeError("upload_video requires http_client in non-dry-run mode")
        headers = {"Authorization": f"Bearer {access_token}"}
        files = {"video": {"filename": filename, "content": video_bytes}}
        data = {"open_id": open_id, "upload_id": upload_id}
        res = self.http_client.post(self.UPLOAD_URL, headers=headers, data=data, files=files)
        _log.info("upload.video", extra={"data": {"upload_id": upload_id, "size": len(video_bytes)}})
        return res

    def check_upload_status(self, access_token: str, open_id: str, upload_id: str) -> Mapping[str, Any]:
        if self.dry_run:
            return {"upload_id": upload_id, "open_id": open_id, "status": "processed(dry)"}
        if self.http_client is None:
            raise RuntimeError("check_upload_status requires http_client in non-dry-run mode")
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"open_id": open_id, "upload_id": upload_id}
        res = self.http_client.get(self.CHECK_URL, headers=headers, params=params)
        _log.info("upload.status", extra={"data": {"upload_id": upload_id, "open_id": open_id}})
        return res

    def list_videos(self, access_token: str, open_id: str, *, cursor: int = 0, max_count: int = 10) -> Mapping[str, Any]:
        if self.dry_run:
            items = [
                {"id": f"dry-video-{i}", "title": f"Dry Video #{i}", "open_id": open_id}
                for i in range(cursor, cursor + max_count)
            ]
            return {"videos": items, "cursor": cursor + max_count, "has_more": False}
        if self.http_client is None:
            raise RuntimeError("list_videos requires http_client in non-dry-run mode")
        headers = {"Authorization": f"Bearer {access_token}"}
        params = {"open_id": open_id, "cursor": cursor, "max_count": max_count}
        return self.http_client.get(self.LIST_URL, headers=headers, params=params)

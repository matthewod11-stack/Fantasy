"""
Adapter wiring factory.

Provides a single place to build configured adapters (respecting DRY_RUN,
environment keys, and injected clients) for use by API/CLI/batch.

Note: Actual adapter implementations (OpenAIAdapter, TikTokAdapter,
HeyGenAdapter, TikTokOAuthConfig) are expected to be available under the
adapters.* namespace. In DRY_RUN mode, missing keys are tolerated to enable
local workflows without secrets.

This version preserves prior behavior (dry-run tolerant shims) while improving
type clarity for Pylance by returning Protocol-shaped types instead of shadow
classes. It never re-declares adapter classes at module scope.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Optional, Any, Protocol, Mapping, TYPE_CHECKING

# ---- Adapter Protocols (for type-checkers / Pylance) -------------------------


class OpenAIAdapterLike(Protocol):
    dry_run: bool

    def generate_script(self, request: Any) -> str:
        ...


class HeyGenAdapterLike(Protocol):
    dry_run: bool

    def render_text_to_avatar(self, request: Any) -> Mapping[str, Any]:
        ...

    def poll_status(self, video_id: str) -> Mapping[str, Any]:
        ...


class TikTokAdapterLike(Protocol):
    dry_run: bool

    def build_login_url(self, state: str, scopes: list[str]) -> str: ...
    def exchange_code(self, code: str) -> Any: ...
    def init_upload(self, access_token: str, open_id: str, *, draft: bool = True) -> Mapping[str, Any]: ...
    def upload_video(
        self,
        access_token: str,
        open_id: str,
        upload_id: str,
        video_bytes: bytes,
        *,
        filename: str = "draft.mp4",
    ) -> Mapping[str, Any]: ...
    def check_upload_status(self, access_token: str, open_id: str, upload_id: str) -> Mapping[str, Any]: ...
    def list_videos(self, access_token: str, open_id: str, *, cursor: int = 0, max_count: int = 10) -> Mapping[str, Any]: ...


# For annotations only (no runtime import cost or failures)
if TYPE_CHECKING:
    pass


# ---- Env container -----------------------------------------------------------


@dataclass
class Env:
    OPENAI_API_KEY: Optional[str] = None
    HEYGEN_API_KEY: Optional[str] = None
    TIKTOK_CLIENT_KEY: Optional[str] = None
    TIKTOK_CLIENT_SECRET: Optional[str] = None
    TIKTOK_REDIRECT_URI: Optional[str] = None
    PUBLIC_BASE_URL: Optional[str] = None
    DRY_RUN: bool = False
    # Live toggles (opt-in). When true, builders become strict and will fail
    # fast if creds/imports are missing.
    HEYGEN_LIVE: bool = False
    TIKTOK_LIVE: bool = False
    OPENAI_ENABLED: bool = False
    SLEEPER_ENABLED: bool = False


def _as_bool(value: Optional[str]) -> bool:
    if value is None:
        return False
    v = value.strip().lower()
    return v in {"1", "true", "t", "yes", "y"}


def _req(value: Optional[str]) -> str:
    """Coerce Optional[str] → str for constructors that require str."""
    return value or ""


def load_env() -> Env:
    """Load environment variables into a typed structure.

    DRY_RUN is parsed from strings like "true"/"1" (default False).
    """
    return Env(
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
        HEYGEN_API_KEY=os.getenv("HEYGEN_API_KEY"),
        TIKTOK_CLIENT_KEY=os.getenv("TIKTOK_CLIENT_KEY"),
        TIKTOK_CLIENT_SECRET=os.getenv("TIKTOK_CLIENT_SECRET"),
        TIKTOK_REDIRECT_URI=os.getenv("TIKTOK_REDIRECT_URI"),
        PUBLIC_BASE_URL=os.getenv("PUBLIC_BASE_URL"),
        DRY_RUN=_as_bool(os.getenv("DRY_RUN")),
        HEYGEN_LIVE=_as_bool(os.getenv("HEYGEN_LIVE")),
        TIKTOK_LIVE=_as_bool(os.getenv("TIKTOK_LIVE")),
        OPENAI_ENABLED=_as_bool(os.getenv("OPENAI_ENABLED")),
        SLEEPER_ENABLED=_as_bool(os.getenv("SLEEPER_ENABLED")),
    )


# ---- Builders (import real adapters if available; otherwise shim) ------------


def build_openai(env: Env, client: Optional[Any] = None) -> OpenAIAdapterLike:
    """Construct an OpenAI adapter respecting DRY_RUN."""
    try:
        from adapters.openai_adapter import OpenAIAdapter  # type: ignore
        return OpenAIAdapter(api_key=env.OPENAI_API_KEY, client=client, dry_run=env.DRY_RUN)
    except Exception:
        class _OpenAIAdapterShim:
            def __init__(self, api_key: Optional[str], client: Optional[Any], dry_run: bool) -> None:
                self.api_key = api_key
                self.client = client
                self.dry_run = dry_run

            def generate_script(self, request: Any) -> str:
                prompt = getattr(request, "prompt", "<no-prompt>")
                return f"[dry-run] Script for: {prompt}"

        return _OpenAIAdapterShim(env.OPENAI_API_KEY, client, env.DRY_RUN)


def build_tiktok(env: Env, http_client: Optional[Any] = None) -> TikTokAdapterLike:
    """Construct a TikTok adapter with OAuth config respecting DRY_RUN."""
    try:
        from adapters.tiktok_adapter import TikTokAdapter, TikTokOAuthConfig  # type: ignore
        # Coerce Optional[str] to str for strict dataclass fields
        oauth = TikTokOAuthConfig(
            _req(env.TIKTOK_CLIENT_KEY),
            _req(env.TIKTOK_CLIENT_SECRET),
            _req(env.TIKTOK_REDIRECT_URI),
        )
        return TikTokAdapter(oauth, http_client=http_client, dry_run=env.DRY_RUN)
    except Exception as exc:
        # In live mode (either via Env object or OS env var), surface errors so
        # callers fail fast and logs are noisy. This allows tests that set
        # os.environ via monkeypatch to be respected when callers construct an
        # Env manually.
        live_flag = env.TIKTOK_LIVE or _as_bool(os.getenv("TIKTOK_LIVE"))
        if live_flag:
            raise
        from dataclasses import dataclass as _dc

        @_dc
        class _OAuthCfgShim:
            client_key: Optional[str]
            client_secret: Optional[str]
            redirect_uri: Optional[str]

        class _TikTokShim:
            def __init__(self, oauth_config: _OAuthCfgShim, http_client: Optional[Any], dry_run: bool) -> None:
                self.oauth_config = oauth_config
                self.http_client = http_client
                self.dry_run = dry_run

            def build_login_url(self, state: str, scopes: list[str]) -> str:
                return f"https://www.tiktok.com/auth/authorize/?state={state}&scope={','.join(scopes)}"

            def exchange_code(self, code: str) -> Mapping[str, Any]:
                return {
                    "access_token": "dry-run-access-token",
                    "refresh_token": "dry-run-refresh-token",
                    "open_id": "dry-run-open-id",
                    "expires_in": 0,
                }

            def init_upload(self, access_token: str, open_id: str, *, draft: bool = True) -> Mapping[str, Any]:
                return {"dry_run": True, "upload_id": "dry-run-upload", "upload_type": "draft" if draft else "publish"}

            def upload_video(
                self,
                access_token: str,
                open_id: str,
                upload_id: str,
                video_bytes: bytes,
                *,
                filename: str = "draft.mp4",
            ) -> Mapping[str, Any]:
                return {"dry_run": True, "upload_id": upload_id, "filename": filename}

            def check_upload_status(self, access_token: str, open_id: str, upload_id: str) -> Mapping[str, Any]:
                return {"dry_run": True, "upload_id": upload_id, "status": {"code": 0}}

            def list_videos(self, access_token: str, open_id: str, *, cursor: int = 0, max_count: int = 10) -> Mapping[str, Any]:
                return {"dry_run": True, "videos": [], "cursor": cursor, "max_count": max_count}

        oauth = _OAuthCfgShim(env.TIKTOK_CLIENT_KEY, env.TIKTOK_CLIENT_SECRET, env.TIKTOK_REDIRECT_URI)
        return _TikTokShim(oauth, http_client, env.DRY_RUN)


def build_heygen(env: Env, http_client: Optional[Any] = None) -> HeyGenAdapterLike:
    """Construct a HeyGen adapter respecting DRY_RUN."""
    try:
        from adapters.heygen_adapter import HeyGenAdapter  # type: ignore
        return HeyGenAdapter(api_key=env.HEYGEN_API_KEY, http_client=http_client, dry_run=env.DRY_RUN)
    except Exception as exc:
        live_flag = env.HEYGEN_LIVE or _as_bool(os.getenv("HEYGEN_LIVE"))
        if live_flag:
            raise
        class _HeyGenShim:
            def __init__(self, api_key: Optional[str], http_client: Optional[Any], dry_run: bool) -> None:
                self.api_key = api_key
                self.http_client = http_client
                self.dry_run = dry_run

            def render_text_to_avatar(self, request: Any) -> Mapping[str, Any]:
                return {"dry_run": True, "request": getattr(request, "__dict__", {}), "video_id": "dry-run-video"}

            def poll_status(self, video_id: str) -> Mapping[str, Any]:
                return {
                    "dry_run": True,
                    "video_id": video_id,
                    "status": "completed",
                    "download_url": "https://example.com/dry-run.mp4",
                }

        return _HeyGenShim(env.HEYGEN_API_KEY, http_client, env.DRY_RUN)
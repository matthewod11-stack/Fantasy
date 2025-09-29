"""Integration adapters for external platforms."""
from .openai_adapter import OpenAIAdapter, ScriptRequest
from .tiktok_adapter import TikTokAdapter, TikTokOAuthConfig, TikTokOAuthTokens
from .heygen_adapter import HeyGenAdapter, HeyGenRenderRequest

__all__ = [
    "OpenAIAdapter",
    "ScriptRequest",
    "TikTokAdapter",
    "TikTokOAuthConfig",
    "TikTokOAuthTokens",
    "HeyGenAdapter",
    "HeyGenRenderRequest",
]

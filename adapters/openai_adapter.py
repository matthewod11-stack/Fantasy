"""
OpenAI adapter with dry-run support.

Standard-library only; no external SDK imports. The adapter works with a
lightweight client Protocol so callers can inject a real SDK client or a fake
for tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable, Sequence
import hashlib


@runtime_checkable
class OpenAIClientProtocol(Protocol):
    """Minimal protocol for an OpenAI-like chat completion client.

    Any client implementing this must return a mapping containing a list of
    choices with the assistant message content at
    result["choices"][0]["message"]["content"].
    """

    def create_chat_completion(
        self,
        *,
        model: str,
        messages: Sequence[Mapping[str, str]],
        max_tokens: int,
        temperature: float,
    ) -> Mapping[str, Any]:
        ...


@dataclass(frozen=True)
class ScriptRequest:
    """Parameters for generating a script via LLM."""

    prompt: str
    audience: str | None = None
    tone: str = "energetic"
    max_output_tokens: int = 512
    temperature: float = 0.7
    model: str = "gpt-4o-mini"


class OpenAIAdapter:
    """Wrapper for OpenAI chat completions with dry-run behavior.

    When dry_run=True, generate deterministic content locally without calling
    any networked client.
    """

    def __init__(
        self,
        api_key: str | None,
        *,
        client: OpenAIClientProtocol | None = None,
        dry_run: bool = False,
    ) -> None:
        self.api_key = api_key
        self.client = client
        self.dry_run = bool(dry_run)

    def generate_script(self, request: ScriptRequest) -> str:
        """Generate a script string from a prompt and options.

        Dry-run: return a deterministic stub based on the prompt and options.
        Live: requires an injected client implementing OpenAIClientProtocol.
        """
        if self.dry_run:
            seed = f"{request.prompt}|{request.audience}|{request.tone}|{request.model}|{request.max_output_tokens}|{request.temperature}"
            digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
            return (
                f"[dry-run] script:{digest}\n"
                f"Prompt: {request.prompt[:80]}\n"
                f"Tone: {request.tone}; Audience: {request.audience or 'general'}"
            )

        if self.client is None:
            raise RuntimeError(
                "OpenAIAdapter requires a client in non-dry-run mode. "
                "Inject a client implementing OpenAIClientProtocol."
            )

        messages = [
            {"role": "system", "content": f"You are a helpful, {request.tone} content writer."},
            {"role": "user", "content": request.prompt},
        ]
        result = self.client.create_chat_completion(
            model=request.model,
            messages=messages,
            max_tokens=request.max_output_tokens,
            temperature=request.temperature,
        )
        try:
            return (
                result["choices"][0]["message"]["content"]
            )  # type: ignore[index]
        except Exception as exc:  # pragma: no cover - defensive
            raise RuntimeError(f"Unexpected response shape from client: {result}") from exc

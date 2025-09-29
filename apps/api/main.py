"""
FastAPI application for Fantasy TikTok Engine.

Main API server providing endpoints for fantasy football content generation.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from apps.core import guardrails
from packages.agents.data_agent import fetch_player_context
from packages.agents.script_agent import render_script

from .config import get_settings
from .schemas import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
    PRD_CONTENT_KINDS,
    VersionResponse,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
settings = get_settings()

# Template locations
TEMPLATE_ROOT = Path("templates") / "script_templates"
LEGACY_TEMPLATE_ROOT = Path("prompts") / "templates"
TEMPLATE_FILENAME_OVERRIDES = {
    "start-sit": "start_sit.md",
    "waiver-wire": "waiver_wire.md",
}


def _resolve_template(kind: str) -> Path:
    """Locate a template file for a given content kind."""
    override = TEMPLATE_FILENAME_OVERRIDES.get(kind)
    candidates = []
    if override:
        candidates.append(TEMPLATE_ROOT / override)
    candidates.append(TEMPLATE_ROOT / f"{kind}.md")
    # Allow underscore variant for backward compatibility
    candidates.append(TEMPLATE_ROOT / f"{kind.replace('-', '_')}.md")
    # Legacy fallbacks
    if override:
        candidates.append(LEGACY_TEMPLATE_ROOT / override)
    candidates.append(LEGACY_TEMPLATE_ROOT / f"{kind}.md")
    candidates.append(LEGACY_TEMPLATE_ROOT / f"{kind.replace('-', '_')}.md")

    for path in candidates:
        if path.exists():
            return path
    return Path()


def _parse_header_bool(value: Optional[str]) -> Optional[bool]:
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in {"1", "true", "t", "yes", "y"}:
        return True
    if normalized in {"0", "false", "f", "no", "n"}:
        return False
    return None


# Create FastAPI app
app = FastAPI(
    title="Fantasy TikTok Engine API",
    description="AI-powered fantasy football content generation for TikTok",
    version="0.1.0",
    debug=settings.debug,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@app.get("/version", response_model=VersionResponse)
async def get_version():
    """Get API version."""
    return VersionResponse(version="0.1.0")


@app.post("/generate", response_model=GenerateResponse)
async def generate_content(
    request: GenerateRequest,
    guardrails_strict: Optional[str] = Header(
        None, alias="X-Guardrails-Strict", convert_underscores=False
    ),
):
    """Generate fantasy football content for TikTok."""
    logger.info("Generating %s content for %s (week %s)", request.kind, request.player, request.week)

    try:
        # Validate kind early (Literal already enforces this, but log explicitly for clarity)
        if request.kind not in PRD_CONTENT_KINDS:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Unsupported content kind: {request.kind}")

        context = fetch_player_context(
            player=request.player,
            week=request.week,
            kind=request.kind,
        )

        if isinstance(context, dict) and context.get("blocked"):
            reason = context.get("block_reason") or "blocked by data agent"
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Generation blocked: {reason}")

        template_path = _resolve_template(request.kind)
        if not template_path:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Template not found for kind '{request.kind}'")

        script = render_script(
            kind=request.kind,
            context=context,
            template_path=str(template_path),
        )

        strict_override = _parse_header_bool(guardrails_strict)
        mode_env = os.getenv("GUARDRAILS_LENGTH_MODE", "fail").lower()
        default_mode = "trim" if mode_env == "trim" else "fail"
        mode = "fail" if strict_override is True else "trim" if strict_override is False else default_mode

        guardrail_result = guardrails.enforce_length(script, max_words=70, mode=mode)
        if not guardrail_result.get("ok"):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Guardrail failed: {guardrail_result.get('reason')}",
            )

        final_script = guardrail_result.get("script") or script
        logger.info(
            "Generated script for %s (mode=%s, trimmed=%s, words=%s)",
            request.kind,
            mode,
            guardrail_result.get("trimmed"),
            guardrail_result.get("word_count"),
        )
        return GenerateResponse(ok=True, script=str(final_script))

    except HTTPException as exc:
        logger.warning("Guarded error during generation: %s", exc.detail)
        raise
    except Exception as exc:  # pragma: no cover - safety net
        logger.exception("Unexpected error generating content")
        raise HTTPException(status_code=500, detail=f"Content generation failed: {exc}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)

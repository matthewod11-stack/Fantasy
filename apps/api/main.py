"""
FastAPI application for Fantasy TikTok Engine.

Main API server providing endpoints for fantasy football content generation.
"""

import logging
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .schemas import GenerateRequest, GenerateResponse, HealthResponse, VersionResponse
from packages.agents.data_agent import fetch_player_context
from packages.agents.script_agent import render_script
from apps.core import guardrails
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
settings = get_settings()

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
async def generate_content(request: GenerateRequest):
    """
    Generate fantasy football content for TikTok.
    
    Args:
        request: Content generation parameters
        
    Returns:
        Generated script content
    """
    try:
        logger.info(f"Generating {request.kind} content for {request.player} (Week {request.week})")
        
        # Fetch player context using Data Agent
        context = fetch_player_context(
            player=request.player,
            week=request.week,
            kind=request.kind
        )
        
        # Determine template path based on content kind
        # Prefer canonical templates location, fall back to legacy prompts/templates
        template_map = {
            "start-sit": "templates/script_templates/start_sit.md",
            "waiver-wire": "templates/script_templates/waiver_wire.md",
            "injury-pivot": "templates/script_templates/injury_pivot.md",  # TODO: Create template
            "trade-thermometer": "templates/script_templates/trade_thermometer.md",  # TODO: Create template
        }

        # Fallback map (legacy)
        legacy_map = {
            k: v.replace("templates/script_templates/", "prompts/templates/")
            for k, v in template_map.items()
        }

        template_path = template_map.get(request.kind)
        # If canonical template missing, fall back to legacy path
        import os
        if not template_path or not os.path.exists(template_path):
            template_path = legacy_map.get(request.kind)
        if not template_path:
            raise HTTPException(status_code=400, detail=f"Unsupported content kind: {request.kind}")
        
        # If the data agent indicated the player is blocked (e.g., OUT/IR), stop early
        if isinstance(context, dict) and context.get("blocked"):
            reason = context.get("block_reason") or "blocked by data agent"
            raise HTTPException(status_code=400, detail=f"Generation blocked: {reason}")

        # Generate script using Script Agent
        script = render_script(
            kind=request.kind,
            context=context,
            template_path=template_path
        )

        # Enforce length guardrail after rendering. Mode can be 'fail' or 'trim'.
        mode = os.getenv("GUARDRAILS_LENGTH_MODE", "fail").lower()
        gr = guardrails.enforce_length(script, max_words=70, mode=mode)
        if not gr.get("ok"):
            # Fail fast with a clear message
            raise HTTPException(status_code=400, detail=f"Guardrail failed: {gr.get('reason')}")

        # If trimmed, use trimmed script and indicate in response (note: schema stable)
        final_script = gr.get("script") or script

        logger.info(f"Successfully generated {len(final_script)} character script (words={gr.get('word_count')})")

        return GenerateResponse(ok=True, script=str(final_script))
        
    except Exception as e:
        logger.error(f"Error generating content: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)
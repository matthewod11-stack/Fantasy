"""
Pydantic schemas for Fantasy TikTok Engine API.

Defines request/response models for API endpoints with validation.
"""

from typing import Literal
from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request model for content generation endpoint."""
    
    player: str = Field(..., description="Fantasy football player name", min_length=1)
    week: int = Field(..., description="NFL week number", ge=1, le=18)
    kind: Literal["start-sit", "waiver-wire", "injury-pivot", "trade-thermometer"] = Field(
        ..., description="Type of content to generate"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "player": "Bijan Robinson",
                "week": 5,
                "kind": "start-sit"
            }
        }


class GenerateResponse(BaseModel):
    """Response model for content generation endpoint."""
    
    ok: bool = Field(..., description="Whether the generation was successful")
    script: str = Field(..., description="Generated content script")
    
    class Config:
        schema_extra = {
            "example": {
                "ok": True,
                "script": "🔥 **WEEK 5 START/SIT ALERT** 🔥\n\nShould you start **Bijan Robinson** this week?"
            }
        }


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""
    
    status: str = Field(..., description="Service health status")
    
    class Config:
        schema_extra = {
            "example": {
                "status": "ok"
            }
        }


class VersionResponse(BaseModel):
    """Response model for version endpoint."""
    
    version: str = Field(..., description="API version")
    
    class Config:
        schema_extra = {
            "example": {
                "version": "0.1.0"
            }
        }
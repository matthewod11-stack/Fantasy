"""
Configuration management for Fantasy TikTok Engine API.

Provides centralized configuration loading with environment variable fallbacks.
All settings have sane defaults so the application runs even without .env file.
"""

import os
from typing import Optional
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings with environment variable fallbacks."""
    
    # Server configuration
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    
    # Agent timeouts (seconds)
    data_agent_timeout: int = 30
    script_agent_timeout: int = 60
    voice_agent_timeout: int = 120
    
    # External API keys (optional)
    openai_api_key: Optional[str] = None
    tiktok_client_key: Optional[str] = None
    tiktok_client_secret: Optional[str] = None
    google_sheets_credentials_path: Optional[str] = None
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "json"


def get_settings() -> Settings:
    """
    Load settings from environment variables with fallbacks.
    
    Returns:
        Settings: Configuration object with all application settings
    """
    return Settings(
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        debug=os.getenv("DEBUG", "false").lower() == "true",
        data_agent_timeout=int(os.getenv("DATA_AGENT_TIMEOUT", "30")),
        script_agent_timeout=int(os.getenv("SCRIPT_AGENT_TIMEOUT", "60")),
        voice_agent_timeout=int(os.getenv("VOICE_AGENT_TIMEOUT", "120")),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        tiktok_client_key=os.getenv("TIKTOK_CLIENT_KEY"),
        tiktok_client_secret=os.getenv("TIKTOK_CLIENT_SECRET"),
        google_sheets_credentials_path=os.getenv("GOOGLE_SHEETS_CREDENTIALS_PATH"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_format=os.getenv("LOG_FORMAT", "json"),
    )
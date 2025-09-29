"""
Metrics configuration for Fantasy TikTok Engine.

Provides environment-driven settings with safe defaults so the metrics
subsystem runs even without a `.env` file.
"""
import os
from dataclasses import dataclass


@dataclass
class MetricsSettings:
    SHEETS_ENABLED: bool = False
    SHEETS_SPREADSHEET_ID: str = ""
    SHEETS_SERVICE_ACCOUNT_JSON: str = ""
    METRICS_DIR: str = ".metrics"
    CSV_PATH: str = ".metrics/posts.csv"


def get_metrics_settings() -> MetricsSettings:
    s = MetricsSettings(
        SHEETS_ENABLED=os.getenv("SHEETS_ENABLED", "false").lower() == "true",
        SHEETS_SPREADSHEET_ID=os.getenv("SHEETS_SPREADSHEET_ID", ""),
        SHEETS_SERVICE_ACCOUNT_JSON=os.getenv("SHEETS_SERVICE_ACCOUNT_JSON", ""),
        METRICS_DIR=os.getenv("METRICS_DIR", ".metrics"),
        CSV_PATH=os.getenv("CSV_PATH", os.path.join(os.getenv("METRICS_DIR", ".metrics"), "posts.csv")),
    )
    return s

"""
Pydantic schemas for metrics records.
"""
from pydantic import BaseModel, Field
from typing import Optional


class PostRecord(BaseModel):
    post_id: str
    date: str  # YYYY-MM-DD
    player: Optional[str]
    type: Optional[str]
    views: Optional[int] = 0
    likes: Optional[int] = 0
    comments: Optional[int] = 0
    shares: Optional[int] = 0
    retention_3s: Optional[float] = 0.0
    retention_10s: Optional[float] = 0.0
    ctr: Optional[float] = 0.0
    email_signups: Optional[int] = 0
    utm_campaign: Optional[str] = None
    week: Optional[int] = None


class DailySummary(BaseModel):
    date: str
    total_posts: int
    total_views: int
    total_likes: int
    total_comments: int
    total_shares: int
    total_email_signups: int


class AttributionRecord(BaseModel):
    post_id: str
    utm_source: str = Field(default="tiktok")
    utm_medium: str = Field(default="social")
    utm_campaign: str

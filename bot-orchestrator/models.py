"""Pydantic models for bot orchestrator API"""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class BotCreateRequest(BaseModel):
    """Request to create a new bot"""
    meeting_url: str = Field(..., description="Meeting URL (Google Meet, Zoom, Teams, etc.)")
    bot_name: str = Field(default="Freya", description="Bot display name in meeting")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Custom metadata")


class BotResponse(BaseModel):
    """Response after creating or fetching a bot"""
    bot_id: str
    meeting_url: str
    status: str  # ready, joining, in_call, done, fatal
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TranscriptWebhook(BaseModel):
    """Webhook payload for real-time transcription from Recall.ai"""
    bot_id: str
    event: str  # e.g., "transcript.data"
    participant: Dict[str, Any]  # {id, name}
    text: str
    timestamp: datetime
    words: Optional[List[Dict[str, Any]]] = None  # Word-level timing


class StatusWebhook(BaseModel):
    """Webhook payload for bot status changes from Recall.ai"""
    bot_id: str
    status: str  # ready, joining, in_call, done, fatal
    code: Optional[str] = None
    message: Optional[str] = None
    timestamp: datetime


class BotListResponse(BaseModel):
    """List of bots"""
    bots: List[BotResponse]
    total: int

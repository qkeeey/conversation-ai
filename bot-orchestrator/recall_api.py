"""Recall.ai API client for bot management and audio output"""
import os
import httpx
from typing import Dict, Any, Optional
from datetime import datetime


class RecallAPIClient:
    """Client for Recall.ai bot API"""
    
    def __init__(
        self, 
        api_key: Optional[str] = None, 
        base_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("RECALL_API_KEY")
        self.base_url = (base_url or os.getenv("RECALL_BASE_URL", "https://us-east-1.recall.ai")).rstrip("/")
        
        if not self.api_key:
            raise ValueError("RECALL_API_KEY is required")
        
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            timeout=30.0
        )
    
    async def create_bot(
        self, 
        meeting_url: str,
        bot_name: str = "Freya",
        webhook_base_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new Recall.ai bot
        
        Docs: https://docs.recall.ai/reference/bot_create
        """
        payload = {
            "meeting_url": meeting_url,
            "bot_name": bot_name,
            "transcription_options": {
                "provider": "recall",
                "mode": "prioritize_low_latency"  # Critical for real-time response
            }
        }
        
        # Add webhook URLs if provided
        if webhook_base_url:
            payload["real_time_transcription"] = {
                "destination_url": f"{webhook_base_url}/webhooks/recall/realtime"
            }
            payload["automatic_leave"] = {
                "waiting_room_timeout": 600
            }
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/bot",
            json=payload
        )
        response.raise_for_status()
        return response.json()
    
    async def get_bot(self, bot_id: str) -> Dict[str, Any]:
        """Get bot details from Recall.ai"""
        response = await self.client.get(
            f"{self.base_url}/api/v1/bot/{bot_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def stop_bot(self, bot_id: str) -> Dict[str, Any]:
        """Stop/leave a bot from the meeting"""
        # Note: Check Recall docs for exact endpoint - may be DELETE or POST leave
        response = await self.client.post(
            f"{self.base_url}/api/v1/bot/{bot_id}/leave"
        )
        response.raise_for_status()
        return response.json()
    
    async def send_audio(
        self, 
        bot_id: str, 
        pcm_bytes: bytes,
        sample_rate: int = 16000
    ) -> Dict[str, Any]:
        """
        Send audio to bot for playback in meeting
        
        Docs: https://docs.recall.ai/reference/bot_output_audio_create
        """
        # Note: Recall.ai may accept PCM directly or require base64 encoding
        # Check docs for exact format. Adjusting based on actual API:
        response = await self.client.post(
            f"{self.base_url}/api/v1/bot/{bot_id}/output_audio",
            content=pcm_bytes,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "audio/pcm",
                "X-Sample-Rate": str(sample_rate)
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

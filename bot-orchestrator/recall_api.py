"""Recall.ai API client for bot management and audio output"""
import os
import sys
import json
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
                "Authorization": self.api_key,
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
            "bot_name": bot_name
        }
        
        # Configure real-time audio streaming to our own STT pipeline
        if webhook_base_url:
            # WebSocket URL for receiving mixed audio from Recall
            audio_ws_url = f"{webhook_base_url.replace('https://', 'wss://').replace('http://', 'ws://')}/ws/recall-audio"
            status_webhook_url = f"{webhook_base_url}/webhooks/recall/status"
            
            payload["recording_config"] = {
                # Enable mixed audio streaming (single combined stream)
                "audio_mixed_raw": {},
                # Configure WebSocket endpoint for real-time audio
                "realtime_endpoints": [
                    {
                        "type": "websocket",
                        "url": audio_ws_url,
                        "events": ["audio_mixed_raw.data"]
                    }
                ]
            }
            
            # Add status change webhooks
            payload["bot_config"] = {
                "webhook_url": status_webhook_url
            }
            
            # Note: For real-time audio streaming, use Output Media (start_output_media method)
            # instead of automatic_audio_output + /output_audio/ endpoint
            
            payload["automatic_leave"] = {
                "waiting_room_timeout": 600
            }
            print(f"[INFO] Registering audio WebSocket: {audio_ws_url}", flush=True)
            print(f"[INFO] Registering status webhook: {status_webhook_url}", flush=True)
        else:
            print(f"[WARNING] No webhook_base_url provided - real-time audio will NOT be enabled", flush=True)
        
        print(f"[DEBUG] Bot creation payload: {payload}", flush=True)
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/v1/bot",
                json=payload
            )
            
            # Check for errors and log details
            if response.status_code >= 400:
                error_body = response.text
                print(f"[ERROR] Recall API returned {response.status_code}", flush=True)
                print(f"[ERROR] Request payload: {json.dumps(payload, indent=2)}", flush=True)
                print(f"[ERROR] Response body: {error_body}", flush=True)
                response.raise_for_status()
            
            return response.json()
        except httpx.HTTPStatusError as e:
            # Re-raise with more context
            error_body = e.response.text if hasattr(e, 'response') else "No response body"
            print(f"[ERROR] HTTPStatusError: {e}", flush=True)
            print(f"[ERROR] Response body: {error_body}", flush=True)
            raise
        except Exception as e:
            print(f"[ERROR] Unexpected error calling Recall API: {e}", flush=True)
            raise
    
    async def get_bot(self, bot_id: str) -> Dict[str, Any]:
        """Get bot details from Recall.ai"""
        response = await self.client.get(
            f"{self.base_url}/api/v1/bot/{bot_id}"
        )
        response.raise_for_status()
        return response.json()
    
    async def stop_bot(self, bot_id: str) -> Dict[str, Any]:
        """Stop/leave a bot from the meeting"""
        response = await self.client.post(
            f"{self.base_url}/api/v1/bot/{bot_id}/leave_call/"
        )
        response.raise_for_status()
        return response.json()
    
    async def start_output_media(self, bot_id: str, output_media_url: str) -> Dict[str, Any]:
        """
        Start Output Media for real-time audio streaming to meeting
        
        Docs: https://docs.recall.ai/docs/output-media
        
        Args:
            bot_id: Bot ID
            output_media_url: URL of your webpage that will play audio
        
        Returns:
            Output media session info
        """
        payload = {
            "output_media_url": output_media_url
        }
        
        print(f"[INFO] Starting Output Media for bot {bot_id}: {output_media_url}", flush=True)
        
        response = await self.client.post(
            f"{self.base_url}/api/v1/bot/{bot_id}/output_media/",
            json=payload
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
        Send audio to bot for playback in meeting (DEPRECATED - Use Output Media instead)
        
        NOTE: This endpoint requires automatic_audio_output to be configured during bot creation.
        For real-time streaming, use Output Media via start_output_media() instead.
        
        Docs: https://docs.recall.ai/reference/bot_output_audio_create
        """
        raise NotImplementedError(
            "output_audio endpoint is deprecated. Use Output Media (start_output_media) for real-time audio streaming."
        )
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

"""Redis queue for decoupling webhook receiver from agent worker"""
import json
import redis.asyncio as aioredis
from typing import Dict, Any, Optional
import os


class RedisQueue:
    """Redis-based message queue for transcript events"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client: Optional[aioredis.Redis] = None
        self.binary_client: Optional[aioredis.Redis] = None  # Persistent connection for audio publishing
        self.queue_name = "meeting_events"
    
    async def connect(self):
        """Connect to Redis"""
        self.client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        
        # Also create persistent binary client for audio publishing
        self.binary_client = await aioredis.from_url(
            self.redis_url,
            decode_responses=False  # Keep as bytes for audio
        )
    
    async def enqueue_transcript(self, event: Dict[str, Any]):
        """
        Enqueue a transcript event for processing
        
        Schema:
        {
            "type": "transcript",
            "bot_id": "...",
            "meeting_url": "...",
            "participant": {"id": "...", "name": "..."},
            "text": "...",
            "timestamp": "2026-02-14T12:34:56Z"
        }
        """
        if not self.client:
            await self.connect()
        
        message = json.dumps(event)
        await self.client.lpush(self.queue_name, message)
    
    async def dequeue_transcript(self, timeout: int = 1) -> Optional[Dict[str, Any]]:
        """
        Dequeue a transcript event (blocking)
        
        Returns None if timeout expires with no messages
        """
        if not self.client:
            await self.connect()
        
        result = await self.client.brpop(self.queue_name, timeout=timeout)
        if result:
            _, message = result
            return json.loads(message)
        return None
    
    async def queue_length(self) -> int:
        """Get current queue depth"""
        if not self.client:
            await self.connect()
        return await self.client.llen(self.queue_name)
    
    async def enqueue_audio_chunk(self, event: Dict[str, Any]):
        """
        Enqueue an audio chunk for STT processing
        
        Schema:
        {
            "type": "audio_chunk",
            "bot_id": "...",
            "meeting_url": "...",
            "audio_data": "hex_string",  # PCM S16LE data as hex
            "sample_rate": 16000,
            "timestamp": "2026-02-14T12:34:56Z"
        }
        """
        if not self.client:
            await self.connect()
        
        event["type"] = "audio_chunk"
        message = json.dumps(event)
        await self.client.lpush(self.queue_name, message)
    
    async def publish_audio_output(self, bot_id: str, audio_data: bytes):
        """
        Publish TTS audio output to Output Media WebSocket
        
        Uses Redis pub/sub for real-time streaming
        Now uses persistent connection for efficiency (no connection overhead per chunk)
        """
        if not self.binary_client:
            await self.connect()
        
        channel = f"audio_output:{bot_id}"
        
        # Use persistent binary client (reused across all chunks)
        await self.binary_client.publish(channel, audio_data)
        
        print(f"📡 [REDIS-PUB] Published {len(audio_data)} bytes to {channel}", flush=True)
    
    async def close(self):
        """Close Redis connections"""
        if self.client:
            await self.client.close()
        if self.binary_client:
            await self.binary_client.close()

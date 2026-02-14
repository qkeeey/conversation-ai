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
        self.queue_name = "meeting_events"
    
    async def connect(self):
        """Connect to Redis"""
        self.client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
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
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()

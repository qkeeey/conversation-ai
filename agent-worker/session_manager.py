"""Session management for bot conversations"""
import json
from typing import Dict, Any, List, Optional
import redis.asyncio as aioredis
import os


class SessionManager:
    """Redis-backed session store for bot conversation history"""
    
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client: Optional[aioredis.Redis] = None
        self.max_history = 10  # Keep last 10 turns
        self.session_ttl = 3600  # 1 hour expiry
    
    async def connect(self):
        """Connect to Redis"""
        self.client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    def _session_key(self, bot_id: str) -> str:
        """Generate Redis key for session"""
        return f"session:{bot_id}"
    
    async def get_session(self, bot_id: str) -> Dict[str, Any]:
        """
        Get or create session for bot
        
        Returns:
        {
            "bot_id": "...",
            "history": [{"role": "user", "text": "..."}, ...],
            "context": {...}
        }
        """
        if not self.client:
            await self.connect()
        
        key = self._session_key(bot_id)
        data = await self.client.get(key)
        
        if data:
            return json.loads(data)
        
        # Create new session
        session = {
            "bot_id": bot_id,
            "history": [],
            "context": {}
        }
        return session
    
    async def add_message(self, bot_id: str, role: str, text: str):
        """
        Add a message to conversation history
        
        Args:
            bot_id: Bot identifier
            role: "user" or "assistant"
            text: Message text
        """
        if not self.client:
            await self.connect()
        
        session = await self.get_session(bot_id)
        
        # Add new message
        session["history"].append({
            "role": role,
            "content": text
        })
        
        # Keep only last N messages
        if len(session["history"]) > self.max_history:
            session["history"] = session["history"][-self.max_history:]
        
        # Save back to Redis with TTL
        key = self._session_key(bot_id)
        await self.client.setex(
            key,
            self.session_ttl,
            json.dumps(session)
        )
    
    async def get_history(self, bot_id: str) -> List[Dict[str, str]]:
        """Get conversation history for bot"""
        session = await self.get_session(bot_id)
        return session.get("history", [])
    
    async def clear_session(self, bot_id: str):
        """Clear session (e.g., when bot leaves meeting)"""
        if not self.client:
            await self.connect()
        
        key = self._session_key(bot_id)
        await self.client.delete(key)
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()

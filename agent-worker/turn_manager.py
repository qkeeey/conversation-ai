"""Turn-taking logic for meeting bot"""
import redis.asyncio as aioredis
from typing import Optional
import os


class TurnManager:
    """Manages when bot should speak and handle interruptions"""
    
    def __init__(self, redis_url: Optional[str] = None, bot_name: str = "Freya"):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.client: Optional[aioredis.Redis] = None
        self.bot_name = bot_name.lower()
        self.speaking_ttl = 30  # Max 30 seconds speaking duration tracking
    
    async def connect(self):
        """Connect to Redis"""
        self.client = await aioredis.from_url(
            self.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
    
    def _speaking_key(self, bot_id: str) -> str:
        """Generate Redis key for speaking state"""
        return f"bot:speaking:{bot_id}"
    
    def should_respond(self, text: str, participant_name: str) -> bool:
        """
        Decide if bot should respond to this utterance
        
        Rules (MVP):
        1. Don't respond if participant is the bot itself (prevent echo)
        2. Only respond if utterance contains bot name (wake word)
        
        Args:
            text: Utterance text
            participant_name: Speaker name
        
        Returns:
            True if bot should respond
        """
        should_respond, _ = self.should_respond_with_reason(text, participant_name)
        return should_respond
    
    def should_respond_with_reason(self, text: str, participant_name: str) -> tuple[bool, str]:
        """
        Decide if bot should respond with detailed reasoning
        
        Returns:
            (should_respond: bool, reason: str)
        """
        text_lower = text.lower()
        participant_lower = participant_name.lower() if participant_name else ""
        
        print(f"🔍 [WAKE-WORD] Checking: '{text}'")
        print(f"🔍 [WAKE-WORD] Looking for: '{self.bot_name}'")
        print(f"🔍 [WAKE-WORD] Speaker: '{participant_name}'")
        
        # Rule 1: Don't respond to self
        if participant_name and self.bot_name in participant_lower:
            print(f"❌ [WAKE-WORD] Rejected: Self-speech")
            return False, f"Self-speech detected (speaker: {participant_name})"
        
        # Rule 2: Wake word detection (bot name mention) - add fuzzy matching
        # Check exact match first
        if self.bot_name in text_lower:
            print(f"✅ [WAKE-WORD] Accepted: Exact match found")
            return True, f"Wake word '{self.bot_name}' detected"
        
        # Fuzzy matching for common misspellings ("afreyya" -> "freya")
        import re
        # Remove punctuation and extra spaces
        cleaned = re.sub(r'[^a-z\s]', '', text_lower)
        words = cleaned.split()
        
        for word in words:
            # Check Levenshtein distance or simple pattern matching
            if 'frey' in word or 'afrey' in word:
                print(f"✅ [WAKE-WORD] Accepted: Fuzzy match '{word}' ~ '{self.bot_name}'")
                return True, f"Wake word fuzzy match: '{word}' ~ '{self.bot_name}'"
        
        print(f"❌ [WAKE-WORD] Rejected: No wake word found")
        return False, f"No wake word '{self.bot_name}' found (checked: {words[:5]})"
    
    def should_interrupt(self, text: str) -> bool:
        """
        Decide if new utterance should interrupt bot's current response
        
        Args:
            text: New utterance text
        
        Returns:
            True if should cancel current response and start new one
        """
        # Interrupt if bot name is mentioned (direct address)
        return self.bot_name in text.lower()
    
    async def is_speaking(self, bot_id: str) -> bool:
        """Check if bot is currently speaking"""
        if not self.client:
            await self.connect()
        
        key = self._speaking_key(bot_id)
        value = await self.client.get(key)
        return value is not None
    
    async def set_speaking(self, bot_id: str, speaking: bool):
        """
        Update bot speaking state
        
        Args:
            bot_id: Bot identifier
            speaking: True when bot starts speaking, False when done
        """
        if not self.client:
            await self.connect()
        
        key = self._speaking_key(bot_id)
        
        if speaking:
            # Set with TTL (auto-expire if we miss the "done" signal)
            await self.client.setex(key, self.speaking_ttl, "true")
        else:
            # Clear speaking state
            await self.client.delete(key)
    
    async def close(self):
        """Close Redis connection"""
        if self.client:
            await self.client.close()

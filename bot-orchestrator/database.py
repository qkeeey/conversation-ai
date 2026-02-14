"""SQLite database management for bot orchestrator"""
import json
import aiosqlite
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path


class BotDatabase:
    """Async SQLite database for bot state management"""
    
    def __init__(self, db_path: str = "data/bots.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def initialize(self):
        """Create tables if they don't exist"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bots (
                    bot_id TEXT PRIMARY KEY,
                    meeting_url TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata_json TEXT
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bot_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT,
                    received_at TEXT NOT NULL,
                    FOREIGN KEY (bot_id) REFERENCES bots (bot_id)
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_bot_events_bot_id 
                ON bot_events(bot_id)
            """)
            await db.commit()
    
    async def create_bot(
        self, 
        bot_id: str, 
        meeting_url: str, 
        status: str = "ready",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new bot record"""
        now = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata or {})
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO bots (bot_id, meeting_url, status, created_at, updated_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (bot_id, meeting_url, status, now, now, metadata_json))
            await db.commit()
        
        return {
            "bot_id": bot_id,
            "meeting_url": meeting_url,
            "status": status,
            "created_at": now,
            "metadata": metadata or {}
        }
    
    async def get_bot(self, bot_id: str) -> Optional[Dict[str, Any]]:
        """Get bot by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM bots WHERE bot_id = ?", (bot_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                return {
                    "bot_id": row["bot_id"],
                    "meeting_url": row["meeting_url"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "metadata": json.loads(row["metadata_json"])
                }
    
    async def update_bot_status(self, bot_id: str, status: str) -> bool:
        """Update bot status"""
        now = datetime.utcnow().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE bots 
                SET status = ?, updated_at = ?
                WHERE bot_id = ?
            """, (status, now, bot_id))
            await db.commit()
            return True
    
    async def list_bots(self, limit: int = 100) -> List[Dict[str, Any]]:
        """List all bots"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM bots ORDER BY created_at DESC LIMIT ?", (limit,)
            ) as cursor:
                rows = await cursor.fetchall()
                return [{
                    "bot_id": row["bot_id"],
                    "meeting_url": row["meeting_url"],
                    "status": row["status"],
                    "created_at": row["created_at"],
                    "metadata": json.loads(row["metadata_json"])
                } for row in rows]
    
    async def log_event(
        self, 
        bot_id: str, 
        event_type: str, 
        payload: Optional[Dict[str, Any]] = None
    ):
        """Log a bot event for debugging"""
        now = datetime.utcnow().isoformat()
        
        # Custom JSON encoder to handle datetime objects
        def json_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Type {type(obj)} not serializable")
        
        payload_json = json.dumps(payload or {}, default=json_serializer)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO bot_events (bot_id, event_type, payload_json, received_at)
                VALUES (?, ?, ?, ?)
            """, (bot_id, event_type, payload_json, now))
            await db.commit()

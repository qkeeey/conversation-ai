"""FastAPI bot orchestrator service for Recall.ai integration"""
import os
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from models import (
    BotCreateRequest, 
    BotResponse, 
    BotListResponse,
    TranscriptWebhook, 
    StatusWebhook
)
from database import BotDatabase
from recall_api import RecallAPIClient
from redis_queue import RedisQueue


# Global instances
db: Optional[BotDatabase] = None
recall_client: Optional[RecallAPIClient] = None
redis_queue: Optional[RedisQueue] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db, recall_client, redis_queue
    
    # Startup
    print("🚀 Starting Bot Orchestrator Service...")
    
    db = BotDatabase()
    await db.initialize()
    print("✅ Database initialized")
    
    recall_client = RecallAPIClient()
    print("✅ Recall.ai client initialized")
    
    redis_queue = RedisQueue()
    await redis_queue.connect()
    print("✅ Redis queue connected")
    
    print("🎉 Bot Orchestrator ready!")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")
    if recall_client:
        await recall_client.close()
    if redis_queue:
        await redis_queue.close()


app = FastAPI(
    title="Conversation AI - Bot Orchestrator",
    description="Manages Recall.ai bots and webhook events",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    queue_length = await redis_queue.queue_length() if redis_queue else -1
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "queue_depth": queue_length
    }


@app.post("/v1/bots", response_model=BotResponse, status_code=status.HTTP_201_CREATED)
async def create_bot(request: BotCreateRequest):
    """
    Create a new Recall.ai bot and join meeting
    
    This will:
    1. Call Recall.ai API to create bot
    2. Save bot state to database
    3. Return bot details
    """
    try:
        # Get public webhook base URL
        webhook_base_url = os.getenv("PUBLIC_BASE_URL")
        
        # Create bot via Recall.ai
        recall_response = await recall_client.create_bot(
            meeting_url=request.meeting_url,
            bot_name=request.bot_name,
            webhook_base_url=webhook_base_url
        )
        
        bot_id = recall_response["id"]
        
        # Save to database
        bot_data = await db.create_bot(
            bot_id=bot_id,
            meeting_url=request.meeting_url,
            status=recall_response.get("status", "ready"),
            metadata=request.metadata
        )
        
        # Log event
        await db.log_event(bot_id, "bot.created", recall_response)
        
        print(f"✅ Created bot {bot_id} for meeting: {request.meeting_url}")
        
        return BotResponse(**bot_data)
    
    except Exception as e:
        print(f"❌ Error creating bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bot: {str(e)}"
        )


@app.get("/v1/bots/{bot_id}", response_model=BotResponse)
async def get_bot(bot_id: str):
    """Get bot details"""
    bot = await db.get_bot(bot_id)
    if not bot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bot {bot_id} not found"
        )
    return BotResponse(**bot)


@app.delete("/v1/bots/{bot_id}")
async def stop_bot(bot_id: str):
    """Stop bot and leave meeting"""
    try:
        # Check if bot exists
        bot = await db.get_bot(bot_id)
        if not bot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Bot {bot_id} not found"
            )
        
        # Stop bot via Recall.ai
        await recall_client.stop_bot(bot_id)
        
        # Update status
        await db.update_bot_status(bot_id, "stopped")
        
        # Log event
        await db.log_event(bot_id, "bot.stopped", {})
        
        print(f"✅ Stopped bot {bot_id}")
        
        return {"message": f"Bot {bot_id} stopped successfully"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error stopping bot: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to stop bot: {str(e)}"
        )


@app.get("/v1/bots", response_model=BotListResponse)
async def list_bots(limit: int = 100):
    """List all bots"""
    bots = await db.list_bots(limit=limit)
    return BotListResponse(
        bots=[BotResponse(**bot) for bot in bots],
        total=len(bots)
    )


@app.post("/webhooks/recall/status")
async def webhook_bot_status(webhook: StatusWebhook):
    """
    Receive bot status change webhooks from Recall.ai
    
    Docs: https://docs.recall.ai/docs/bot-status-change-events
    """
    try:
        print(f"📥 Status webhook: {webhook.bot_id} -> {webhook.status}")
        
        # Update bot status in database
        await db.update_bot_status(webhook.bot_id, webhook.status)
        
        # Log event
        await db.log_event(webhook.bot_id, "status.change", webhook.dict())
        
        return {"message": "Status received"}
    
    except Exception as e:
        print(f"❌ Error processing status webhook: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


@app.post("/webhooks/recall/realtime")
async def webhook_transcript(request: Request):
    """
    Receive real-time transcript webhooks from Recall.ai
    
    Docs: https://docs.recall.ai/docs/bot-real-time-transcription
    
    This is the critical path: transcript arrives -> enqueue to Redis -> return 200 ASAP
    """
    try:
        # Parse webhook payload
        payload = await request.json()
        
        # Extract transcript data
        bot_id = payload.get("bot_id")
        event_type = payload.get("event", "transcript.data")
        
        # Only process transcript events
        if event_type != "transcript.data":
            return {"message": "Ignored non-transcript event"}
        
        participant = payload.get("participant", {})
        text = payload.get("text", "")
        timestamp = payload.get("timestamp", datetime.utcnow().isoformat())
        
        if not text or not bot_id:
            return {"message": "Missing text or bot_id"}
        
        # Get meeting URL from database
        bot = await db.get_bot(bot_id)
        meeting_url = bot["meeting_url"] if bot else ""
        
        # Normalize and enqueue
        event = {
            "type": "transcript",
            "bot_id": bot_id,
            "meeting_url": meeting_url,
            "participant": participant,
            "text": text,
            "timestamp": timestamp
        }
        
        await redis_queue.enqueue_transcript(event)
        
        print(f"📝 Transcript enqueued: {participant.get('name', 'Unknown')}: {text[:50]}...")
        
        # Log to database (optional, for debugging)
        await db.log_event(bot_id, "transcript.received", event)
        
        return {"message": "Transcript received"}
    
    except Exception as e:
        print(f"❌ Error processing transcript webhook: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

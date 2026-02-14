"""FastAPI bot orchestrator service for Recall.ai integration"""
import os
import asyncio
import struct
from datetime import datetime
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request, status, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
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
from webhook_verifier import verify_webhook_signature
from redis_queue import RedisQueue
from audio_processor import AudioProcessor


# Global instances
db: Optional[BotDatabase] = None
recall_client: Optional[RecallAPIClient] = None
redis_queue: Optional[RedisQueue] = None
audio_processor: Optional[AudioProcessor] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events"""
    global db, recall_client, redis_queue, audio_processor
    
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
    
    audio_processor = AudioProcessor()
    await audio_processor.initialize()
    print("✅ Audio processor initialized")
    
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
        print(f"[DEBUG] PUBLIC_BASE_URL from env: {webhook_base_url}", flush=True)
        
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
        error_msg = str(e)
        print(f"❌ Error creating bot: {error_msg}")
        
        # Try to extract more details from httpx exception
        if hasattr(e, 'response'):
            try:
                error_body = e.response.text
                print(f"   Recall API response body: {error_body}")
            except:
                pass
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bot: {error_msg}"
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
        result = await recall_client.stop_bot(bot_id)
        
        # Update status
        await db.update_bot_status(bot_id, "stopped")
        
        # Log event
        await db.log_event(bot_id, "bot.stopped", result)
        
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
async def webhook_bot_status(
    request: Request,
    x_recall_signature: Optional[str] = Header(None, alias="X-Recall-Signature")
):
    """
    Receive bot status change webhooks from Recall.ai
    
    Docs: https://docs.recall.ai/docs/bot-status-change-events
    
    IMPORTANT: Accepts raw JSON to avoid Pydantic 422 errors on schema mismatch
    """
    try:
        # Verify webhook signature
        body = await request.body()
        if not verify_webhook_signature(body, x_recall_signature):
            print(f"⚠️  Invalid webhook signature for status update", flush=True)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Parse raw JSON (avoid Pydantic validation that causes 422)
        import json
        payload = json.loads(body)
        print(f"\n[STATUS-RAW] Received webhook:", flush=True)
        print(json.dumps(payload, indent=2), flush=True)
        
        # Try multiple common layouts from Recall
        bot_id = payload.get("bot_id") or payload.get("data", {}).get("bot_id") or payload.get("data", {}).get("id")
        status_val = payload.get("status") or payload.get("data", {}).get("status") or payload.get("event", "")
        
        print(f"📥 Status webhook parsed: bot_id={bot_id} status={status_val}", flush=True)
        
        if bot_id:
            # Update bot status in database
            await db.update_bot_status(bot_id, str(status_val))
            
            # Log event
            await db.log_event(bot_id, "status.change", payload)
        
        # Start Output Media for multiple possible "ready" states
        if bot_id and status_val in {"in_call_recording", "in_call", "recording", "in_call_recording.ready"}:
            print(f"🎬 [OUTPUT-MEDIA] Bot {bot_id} status={status_val}, starting Output Media...", flush=True)
            try:
                # Get public webhook URL from environment
                public_base_url = os.getenv("PUBLIC_BASE_URL", "")
                print(f"[DEBUG] PUBLIC_BASE_URL: {public_base_url}", flush=True)
                
                if public_base_url:
                    output_media_url = f"{public_base_url}/output-media.html?bot_id={bot_id}"
                    print(f"🎯 [OUTPUT-MEDIA] Starting with URL: {output_media_url}", flush=True)
                    
                    result = await recall_client.start_output_media(bot_id, output_media_url)
                    print(f"✅ [OUTPUT-MEDIA] Started for bot {bot_id}: {result}", flush=True)
                    print(f"👀 [OUTPUT-MEDIA] Watch for: GET /output-media.html and WS /ws/output-media", flush=True)
                else:
                    print(f"❌ [OUTPUT-MEDIA] PUBLIC_BASE_URL not configured, Output Media will NOT work!", flush=True)
                    print(f"   Set PUBLIC_BASE_URL environment variable to your ngrok/public URL", flush=True)
            except Exception as e:
                print(f"❌ [OUTPUT-MEDIA] Failed to start for bot {bot_id}: {e}", flush=True)
                import traceback
                traceback.print_exc()
        
        return {"ok": True}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error processing status webhook: {e}", flush=True)
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


@app.post("/webhooks/recall/realtime")
async def webhook_transcript(
    request: Request,
    x_recall_signature: Optional[str] = Header(None, alias="X-Recall-Signature")
):
    """
    Receive real-time transcript webhooks from Recall.ai
    
    Docs: https://docs.recall.ai/docs/bot-real-time-transcription
    
    This is the critical path: transcript arrives -> enqueue to Redis -> return 200 ASAP
    """
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # RAW LOGGING - See actual payload structure
        import json
        payload = json.loads(body)
        print(f"\n{'='*60}")
        print(f"[WEBHOOK-RAW] Received webhook:")
        print(f"[WEBHOOK-RAW] Event: {payload.get('event')}")
        print(f"[WEBHOOK-RAW] Full payload: {json.dumps(payload, indent=2)}")
        print(f"{'='*60}\n", flush=True)
        
        # Verify webhook signature
        if not verify_webhook_signature(body, x_recall_signature):
            print(f"⚠️  Invalid webhook signature for transcript")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature"
            )
        
        # Extract event type
        event_type = payload.get("event", "")
        
        # Only process transcript events
        if not event_type.startswith("transcript."):
            print(f"[WEBHOOK] Ignoring non-transcript event: {event_type}")
            return {"message": "Ignored non-transcript event"}
        
        # Parse Recall's actual payload structure:
        # { "event": "transcript.data", "data": { "data": { "words": [...], "participant": {...} }, "bot_id": "..." } }
        data_wrapper = payload.get("data", {})
        bot_id = data_wrapper.get("bot_id")
        transcript_data = data_wrapper.get("data", {})
        
        # Extract text from words array
        words = transcript_data.get("words", [])
        text = " ".join(word.get("text", "") for word in words).strip()
        
        participant = transcript_data.get("participant", {})
        timestamp = transcript_data.get("timestamp", datetime.utcnow().isoformat())
        
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
        
        print(f"\n{'='*70}")
        print(f"📥 [WEBHOOK] Transcript received from Recall.ai")
        print(f"   Bot ID: {bot_id[:8]}...")
        print(f"   Speaker: {participant.get('name', 'Unknown')}")
        print(f"   Text: {text}")
        print(f"   Timestamp: {timestamp}")
        
        await redis_queue.enqueue_transcript(event)
        
        queue_depth = await redis_queue.queue_length()
        print(f"   ✅ Enqueued to Redis (queue depth: {queue_depth})")
        print(f"{'='*70}\n")
        
        # Log to database (optional, for debugging)
        await db.log_event(bot_id, "transcript.received", event)
        
        return {"message": "Transcript received"}
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error processing transcript webhook: {e}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": str(e)}
        )


@app.websocket("/ws/recall-audio")
async def websocket_recall_audio(websocket: WebSocket):
    """
    WebSocket endpoint to receive real-time audio from Recall.ai
    
    Recall sends JSON messages with event "audio_mixed_raw.data":
    {
        "event": "audio_mixed_raw.data",
        "data": {
            "bot_id": "actual_bot_id",  // <- USE THIS
            "recording": {"id": "recording_id_not_bot_id"},  // <- DO NOT USE as bot_id
            "data": {
                "buffer": "base64_encoded_pcm_audio",
                "offset": 123456
            }
        }
    }
    
    Audio format: mono 16-bit signed little-endian PCM at 16 kHz
    
    This endpoint:
    1. Receives JSON messages with base64 audio from Recall
    2. Decodes and processes through STT service
    3. Publishes transcript events to Redis queue
    """
    
    def _extract_bot_id_from_audio_msg(message: dict) -> Optional[str]:
        """
        Extract bot_id from Recall audio message (NOT recording.id!)
        
        recording.id is the RECORDING ID, not the BOT ID
        """
        d = message.get("data", {}) or {}
        
        # Most reliable: explicit bot_id at top level of data
        bot_id = d.get("bot_id")
        if bot_id:
            return bot_id
        
        # Alternative: nested under bot object
        bot_id = d.get("bot", {}).get("id")
        if bot_id:
            return bot_id
        
        # Sometimes nested under recording as bot_id (NOT id)
        bot_id = d.get("recording", {}).get("bot_id")
        if bot_id:
            return bot_id
        
        # Fallback: NO bot_id found
        return None
    
    await websocket.accept()
    print(f"🎙️  [AUDIO-WS] Connected", flush=True)
    
    bot_id = None
    meeting_url = None
    first_message_logged = False
    
    try:
        while True:
            # Receive JSON message from Recall
            message = await websocket.receive_json()
            
            event = message.get("event", "")
            
            # DEBUG: Print full message ONCE to see structure
            if not first_message_logged:
                print(f"\n{'='*70}", flush=True)
                print(f"[DEBUG] Full audio message structure:", flush=True)
                import json
                print(json.dumps(message, indent=2)[:2000], flush=True)  # First 2000 chars
                print(f"{'='*70}\n", flush=True)
                first_message_logged = True
            
            if event != "audio_mixed_raw.data":
                print(f"⚠️  [AUDIO-WS] Skipping non-audio event: {event}", flush=True)
                continue
            
            # Extract bot_id CORRECTLY (not recording.id!)
            if not bot_id:
                recording_id = message.get("data", {}).get("recording", {}).get("id", "unknown")
                extracted_bot_id = _extract_bot_id_from_audio_msg(message)
                
                print(f"🔍 [AUDIO-WS] recording.id={recording_id} extracted_bot_id={extracted_bot_id}", flush=True)
                
                if not extracted_bot_id:
                    print(f"❌ [AUDIO-WS] Could not extract bot_id from message. Recording ID is NOT bot ID!", flush=True)
                    print(f"   Available keys in data: {list(message.get('data', {}).keys())}", flush=True)
                    # Continue to try next message
                    continue
                
                bot_id = extracted_bot_id
                print(f"🎙️  [AUDIO-WS] ✅ Bot ID identified: {bot_id}", flush=True)
                
                # Get meeting URL from database
                bot = await db.get_bot(bot_id)
                if bot:
                    meeting_url = bot.get("meeting_url", "")
                    print(f"✅ [AUDIO-WS] Bot found in DB: {meeting_url[:50]}...", flush=True)
                else:
                    print(f"⚠️  [AUDIO-WS] Bot not found in DB: {bot_id}", flush=True)
            
            if not bot_id:
                print(f"⚠️  [AUDIO-WS] No bot_id yet, skipping audio data", flush=True)
                continue
            
            # Extract and decode audio buffer
            audio_data_b64 = message.get("data", {}).get("data", {}).get("buffer", "")
            
            if audio_data_b64:
                import base64
                audio_bytes = base64.b64decode(audio_data_b64)
                # Only log occasionally to reduce spam
                if len(audio_bytes) > 0:
                    # Process through STT
                    await audio_processor.process_audio_chunk(
                        bot_id=bot_id,
                        meeting_url=meeting_url or "",
                        audio_data=audio_bytes,
                        sample_rate=16000
                    )
            else:
                print(f"⚠️  [AUDIO-WS] No audio buffer in message", flush=True)
    
    except WebSocketDisconnect:
        print(f"🔌 [AUDIO-WS] Disconnected{f': bot_id={bot_id}' if bot_id else ''}", flush=True)
        if bot_id:
            await audio_processor.cleanup_bot_session(bot_id)
    except Exception as e:
        print(f"❌ [AUDIO-WS] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        if bot_id:
            await audio_processor.cleanup_bot_session(bot_id)
    
    except Exception as e:
        print(f"❌ [AUDIO-WS] Setup error: {e}", flush=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass


@app.post("/v1/bots/{bot_id}/output_media")
async def start_bot_output_media(bot_id: str):
    """
    Start Output Media for a bot to enable real-time audio streaming to meeting
    
    This starts a webpage that connects via WebSocket to receive TTS audio chunks
    and plays them back into the meeting.
    """
    try:
        # Get public base URL
        public_base_url = os.getenv("PUBLIC_BASE_URL")
        if not public_base_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="PUBLIC_BASE_URL not configured"
            )
        
        # Output Media webpage URL (we'll create this)
        output_media_url = f"{public_base_url}/output-media.html?bot_id={bot_id}"
        
        # Start Output Media via Recall API
        result = await recall_client.start_output_media(bot_id, output_media_url)
        
        print(f"✅ Started Output Media for bot {bot_id}", flush=True)
        
        return {
            "bot_id": bot_id,
            "output_media_url": output_media_url,
            "status": "started",
            "result": result
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error starting Output Media: {e}", flush=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start Output Media: {str(e)}"
        )


@app.get("/output-media.html")
async def output_media_page(bot_id: str):
    """
    Output Media webpage that plays audio into the meeting
    
    This page:
    1. Connects to our WebSocket endpoint
    2. Receives PCM audio chunks
    3. Plays them using Web Audio API with scheduling
    """
    print(f"🌐 [OUTPUT-MEDIA] Page requested: bot_id={bot_id}", flush=True)
    print(f"🔍 [OUTPUT-MEDIA] If you see this, Recall successfully loaded the page!", flush=True)
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Freya Output Media</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #1a1a1a;
                color: #ffffff;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                height: 100vh;
                margin: 0;
            }
            .status {
                font-size: 24px;
                margin: 20px;
            }
            .indicator {
                width: 100px;
                height: 100px;
                border-radius: 50%;
                background: #4CAF50;
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.5; }
            }
        </style>
    </head>
    <body>
        <div class="status" id="status">Initializing Freya...</div>
        <div class="indicator"></div>
        
        <script>
            const botId = new URLSearchParams(window.location.search).get('bot_id');
            const statusEl = document.getElementById('status');
            
            // WebSocket connection to receive audio
            const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${wsProtocol}//${window.location.host}/ws/output-media?bot_id=${botId}`;
            
            let audioContext;
            let nextPlayTime = 0;
            const bufferDuration = 0.2; // 200ms buffer
            
            async function init() {
                try {
                    // Initialize Web Audio API
                    audioContext = new (window.AudioContext || window.webkitAudioContext)({
                        sampleRate: 16000
                    });
                    
                    // Connect WebSocket
                    const ws = new WebSocket(wsUrl);
                    ws.binaryType = 'arraybuffer';
                    
                    ws.onopen = () => {
                        statusEl.textContent = 'Freya is Ready 🎤';
                        console.log('[OUTPUT-MEDIA] Connected to audio stream');
                    };
                    
                    ws.onmessage = async (event) => {
                        try {
                            // CRITICAL: Handle AudioContext autoplay suspension
                            if (audioContext.state === 'suspended') {
                                await audioContext.resume();
                                console.log('[OUTPUT-MEDIA] AudioContext resumed from suspended state');
                            }
                            
                            // Normalize incoming data to ArrayBuffer (handle both ArrayBuffer and Blob)
                            let arrayBuffer;
                            if (event.data instanceof ArrayBuffer) {
                                arrayBuffer = event.data;
                            } else if (event.data instanceof Blob) {
                                console.log('[OUTPUT-MEDIA] Converting Blob to ArrayBuffer');
                                arrayBuffer = await event.data.arrayBuffer();
                            } else {
                                console.warn('[OUTPUT-MEDIA] Unknown WebSocket data type:', typeof event.data);
                                return;
                            }
                            
                            // Receive PCM audio chunk
                            const pcmData = new Int16Array(arrayBuffer);
                            if (!pcmData.length) {
                                console.warn('[OUTPUT-MEDIA] Received empty audio chunk');
                                return;
                            }
                            
                            console.log(`[OUTPUT-MEDIA] Received ${pcmData.length} samples (${arrayBuffer.byteLength} bytes)`);
                            
                            // Convert PCM to float32 for Web Audio
                            const floatData = new Float32Array(pcmData.length);
                            for (let i = 0; i < pcmData.length; i++) {
                                floatData[i] = pcmData[i] / 32768.0;
                            }
                            
                            // Create audio buffer
                            const audioBuffer = audioContext.createBuffer(1, floatData.length, 16000);
                            audioBuffer.getChannelData(0).set(floatData);
                            
                            console.log(`[OUTPUT-MEDIA] Created buffer: duration=${audioBuffer.duration.toFixed(3)}s`);
                            
                            // Schedule playback
                            const source = audioContext.createBufferSource();
                            source.buffer = audioBuffer;
                            source.connect(audioContext.destination);
                            
                            // Calculate play time with buffer
                            const now = audioContext.currentTime;
                            if (nextPlayTime < now + bufferDuration) {
                                nextPlayTime = now + bufferDuration;
                            }
                            
                            source.start(nextPlayTime);
                            nextPlayTime += audioBuffer.duration;
                            
                            console.log(`[OUTPUT-MEDIA] ✅ Scheduled playback at ${nextPlayTime.toFixed(3)}s (now=${now.toFixed(3)}s, state=${audioContext.state})`);
                        } catch (err) {
                            console.error('[OUTPUT-MEDIA] ❌ Playback error:', err);
                            console.error('[OUTPUT-MEDIA] Error stack:', err.stack);
                        }
                    };
                    
                    ws.onerror = (err) => {
                        statusEl.textContent = 'Connection Error ⚠️';
                        console.error('[OUTPUT-MEDIA] WebSocket error:', err);
                    };
                    
                    ws.onclose = () => {
                        statusEl.textContent = 'Disconnected 🔌';
                        console.log('[OUTPUT-MEDIA] Disconnected');
                    };
                } catch (err) {
                    statusEl.textContent = 'Initialization Error ❌';
                    console.error('[OUTPUT-MEDIA] Init error:', err);
                }
            }
            
            // Auto-start (required for Output Media)
            init();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content.replace("BOT_ID_PLACEHOLDER", bot_id))


@app.websocket("/ws/output-media")
async def websocket_output_media(websocket: WebSocket, bot_id: str):
    """
    WebSocket endpoint to send TTS audio chunks to Output Media webpage
    
    This endpoint:
    1. Accepts connection from Output Media webpage
    2. Receives audio chunks from agent-worker via Redis pub/sub
    3. Streams them to webpage for playback
    """
    await websocket.accept()
    print(f"🔊 [OUTPUT-MEDIA-WS] Connected: bot_id={bot_id}", flush=True)
    print(f"✅ [OUTPUT-MEDIA-WS] Websocket upgrade successful!", flush=True)
    
    audio_chunk_count = 0
    total_bytes_sent = 0
    
    try:
        # Subscribe to audio output for this bot
        import redis.asyncio as aioredis
        redis_client = await aioredis.from_url(
            os.getenv("REDIS_URL", "redis://redis:6379"),
            decode_responses=False  # We need bytes for audio
        )
        pubsub = redis_client.pubsub()
        pubsub_channel = f"audio_output:{bot_id}"
        await pubsub.subscribe(pubsub_channel)
        
        print(f"🔊 [OUTPUT-MEDIA-WS] Subscribed to {pubsub_channel}", flush=True)
        print(f"👂 [OUTPUT-MEDIA-WS] Waiting for audio chunks from agent-worker...", flush=True)
        
        # Stream audio chunks from Redis to WebSocket
        async for message in pubsub.listen():
            if message["type"] == "message":
                audio_chunk = message["data"]
                if audio_chunk:
                    audio_chunk_count += 1
                    total_bytes_sent += len(audio_chunk)
                    print(f"🎵 [OUTPUT-MEDIA-WS] Chunk #{audio_chunk_count}: Sending {len(audio_chunk)} bytes to webpage (total: {total_bytes_sent} bytes)", flush=True)
                    await websocket.send_bytes(audio_chunk)
            elif message["type"] == "subscribe":
                print(f"✅ [OUTPUT-MEDIA-WS] Successfully subscribed to {pubsub_channel}", flush=True)
    
    except WebSocketDisconnect:
        print(f"🔌 [OUTPUT-MEDIA-WS] Disconnected: bot_id={bot_id} (sent {audio_chunk_count} chunks, {total_bytes_sent} bytes total)", flush=True)
    except Exception as e:
        print(f"❌ [OUTPUT-MEDIA-WS] Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
    finally:
        print(f"🏁 [OUTPUT-MEDIA-WS] Session ended for bot {bot_id}", flush=True)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

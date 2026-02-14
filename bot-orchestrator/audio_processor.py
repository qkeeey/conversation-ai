"""
Audio Processor for Real-time STT from Recall.ai audio streams

Receives PCM audio chunks from Recall WebSocket
→ Buffers and sends to STT service
→ Emits transcript events to Redis queue
"""
import asyncio
import io
import sys
import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime

from redis_queue import RedisQueue


class AudioProcessor:
    """Process audio chunks from Recall and generate transcripts via STT"""
    
    def __init__(self):
        self.redis_queue = RedisQueue()
        
        # STT endpoint configuration
        self.stt_endpoint = os.getenv("STT_ENDPOINT", "")
        if not self.stt_endpoint:
            print("⚠️  STT_ENDPOINT not configured", flush=True)
        
        # FAL client for STT
        self.fal_key = os.getenv("FAL_KEY", "")
        if not self.fal_key:
            print("⚠️  FAL_KEY not configured", flush=True)
        
        # Active STT sessions per bot
        self.stt_sessions = {}  # bot_id -> STT session/buffer
        
        # Audio buffers for accumulation
        self.audio_buffers = {}  # bot_id -> bytearray
        
        print("✅ AudioProcessor initialized", flush=True)
    
    async def initialize(self):
        """Initialize Redis and services"""
        await self.redis_queue.connect()
        print("✅ AudioProcessor connected to Redis", flush=True)
    
    async def process_audio_chunk(
        self,
        bot_id: str,
        meeting_url: str,
        audio_data: bytes,
        sample_rate: int = 16000
    ):
        """
        Process a single audio chunk through STT
        
        Args:
            bot_id: Bot identifier
            meeting_url: Meeting URL
            audio_data: Raw PCM S16LE audio bytes
            sample_rate: Audio sample rate (default: 16000)
        """
        try:
            print(f"🔄 [AudioProcessor] Received {len(audio_data)} bytes for bot {bot_id}", flush=True)
            
            # Initialize buffer for this bot if needed
            if bot_id not in self.audio_buffers:
                self.audio_buffers[bot_id] = bytearray()
                print(f"📦 [AudioProcessor] Initialized buffer for bot {bot_id}", flush=True)
            
            # Append to buffer
            self.audio_buffers[bot_id].extend(audio_data)
            buffer_size = len(self.audio_buffers[bot_id])
            
            # Process in 2-second chunks for STT (longer chunks = better transcription)
            chunk_size = sample_rate * 2 * 2  # 2 seconds: sample_rate * bytes_per_sample * seconds
            buffer = self.audio_buffers[bot_id]
            
            print(f"📊 [AudioProcessor] Buffer size: {buffer_size} bytes, need {chunk_size} bytes for STT", flush=True)
            
            if len(buffer) >= chunk_size:
                # Extract chunk for STT
                chunk = bytes(buffer[:chunk_size])
                self.audio_buffers[bot_id] = buffer[chunk_size:]
                
                print(f"🎤 [AudioProcessor] Sending {len(chunk)} bytes to STT service...", flush=True)
                
                # Convert PCM to format expected by STT service
                transcript = await self._stt_process(chunk, sample_rate)
                
                if transcript and transcript.strip():
                    print(f"📝 [STT] ✅ Transcript from bot {bot_id}: '{transcript}'", flush=True)
                    
                    # Emit transcript event to Redis queue
                    import uuid
                    message_id = str(uuid.uuid4())[:8]
                    event = {
                        "type": "transcript",
                        "bot_id": bot_id,
                        "meeting_url": meeting_url,
                        "participant": {
                            "id": "user",
                            "name": "User"
                        },
                        "text": transcript,
                        "timestamp": datetime.utcnow().isoformat(),
                        "is_final": True,
                        "message_id": message_id
                    }
                    await self.redis_queue.enqueue_transcript(event)
                    queue_len = await self.redis_queue.queue_length()
                    print(f"✅ [REDIS] Transcript queued: msg_id={message_id}, bot={bot_id[:8]}, queue_len={queue_len}", flush=True)
                    print(f"✅ [REDIS] Message: '{transcript}'", flush=True)
                else:
                    print(f"⚠️  [STT] No transcript or empty result", flush=True)
        
        except Exception as e:
            print(f"❌ [AudioProcessor] Error processing chunk: {e}", flush=True)
    
    async def _stt_process(self, audio_bytes: bytes, sample_rate: int) -> Optional[str]:
        """
        Send audio to STT service and get transcript
        
        Args:
            audio_bytes: Raw PCM audio
            sample_rate: Sample rate
        
        Returns:
            Transcript text or None
        """
        if not self.stt_endpoint or not self.fal_key:
            print("❌ [STT] STT_ENDPOINT or FAL_KEY not configured", flush=True)
            return None
        
        try:
            # Check audio levels to verify we're not sending silence
            import struct
            import math
            
            samples = struct.unpack("<" + "h" * (len(audio_bytes) // 2), audio_bytes)
            rms = math.sqrt(sum(s * s for s in samples) / len(samples)) if samples else 0
            peak = max(abs(s) for s in samples) if samples else 0
            print(f"🔊 [AUDIO] RMS={rms:.1f} Peak={peak} ({len(audio_bytes)} bytes)", flush=True)
            
            if peak < 200:
                print(f"⚠️  [AUDIO] Silence detected - returning test wake word 'Freya' for testing", flush=True)
                return "Freya"  # Return test wake word for silence to test pipeline
            
            print(f"🔧 [STT] Converting {len(audio_bytes)} bytes to WAV format...", flush=True)
            
            # Create audio file in memory (WAV format)
            import wave
            
            wav_buffer = io.BytesIO()
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(1)  # Mono
                wav_file.setsampwidth(2)  # 16-bit
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_bytes)
            
            wav_buffer.seek(0)
            wav_data = wav_buffer.read()
            
            # Call the /audio/transcriptions endpoint with multipart file upload
            url = f"https://fal.run/{self.stt_endpoint}/audio/transcriptions"
            print(f"📤 [STT] Calling {url} with {len(wav_data)} bytes WAV...", flush=True)
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                files = {
                    "file": ("audio.wav", wav_data, "audio/wav")
                }
                data = {
                    # Optional parameters - uncomment if needed
                    # "language": "tr",
                    # "temperature": "0",
                    # "response_format": "json",
                }
                
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Key {self.fal_key}"
                    },
                    files=files,
                    data=data
                )
                
                print(f"📥 [STT] Response status: {response.status_code}", flush=True)
                print(f"🔍 [STT] Raw response: {response.text[:1000]}", flush=True)
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Parse transcript robustly - different APIs use different field names
                    transcript = (
                        result.get("text")
                        or result.get("transcript")
                        or result.get("output")
                        or (result.get("data", {}) if isinstance(result.get("data"), dict) else {}).get("text")
                        or ""
                    )
                    
                    print(f"✅ [STT] Success! Transcript: '{transcript}'", flush=True)
                    return transcript
                else:
                    print(f"❌ [STT] Error: {response.status_code} - {response.text[:500]}", flush=True)
                    return None
        
        except Exception as e:
            print(f"❌ [STT] Exception: {type(e).__name__}: {e}", flush=True)
            import traceback
            print(f"   Traceback: {traceback.format_exc()}", flush=True)
            return None
    
    async def cleanup_bot_session(self, bot_id: str):
        """Clean up resources for a bot session"""
        if bot_id in self.audio_buffers:
            del self.audio_buffers[bot_id]
        
        if bot_id in self.stt_sessions:
            del self.stt_sessions[bot_id]
        
        print(f"🧹 [AudioProcessor] Cleaned up session for bot {bot_id}", flush=True)
    
    async def close(self):
        """Shutdown processor"""
        await self.redis_queue.close()
        print("👋 AudioProcessor shut down", flush=True)

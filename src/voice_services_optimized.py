"""
Ultra-Optimized Voice Services with True Streaming
- LLM streaming with chunked TTS
- True PCM streaming playback
- In-memory audio handling
- Aggressive latency optimization
"""
import requests
import aiohttp
import asyncio
import base64
import struct
from typing import Optional, AsyncIterator, Tuple
from pathlib import Path
from io import BytesIO
from config import Config
import time


class VoiceServicesOptimized:
    """Ultra-low-latency voice services with streaming everything"""
    
    def __init__(self):
        self.fal_key = Config.FAL_KEY
        self._session = None
        self._requests_session = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create async HTTP session (connection pooling)"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=60, connect=10, sock_read=30)
            connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
            # Set larger read buffer for SSE with large chunks
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
                read_bufsize=2**20  # 1MB buffer for large base64 PCM chunks
            )
        return self._session
    
    def get_requests_session(self) -> requests.Session:
        """Get or create requests session for sync operations"""
        if self._requests_session is None:
            self._requests_session = requests.Session()
            self._requests_session.headers.update({
                "User-Agent": "ConversationAI/1.0"
            })
        return self._requests_session
    
    # ===== STT (In-Memory, No Disk) =====
    
    async def transcribe_audio_bytes_async(self, audio_bytes: bytes, 
                                           filename: str = "audio.wav") -> Tuple[str, float]:
        """
        Transcribe audio from memory (no disk write) with timing
        
        Args:
            audio_bytes: WAV audio data in memory
            filename: Filename for multipart upload (metadata only)
        
        Returns:
            Tuple of (transcribed_text, latency_seconds)
        """
        session = await self.get_session()
        
        # Create multipart form data from bytes
        data = aiohttp.FormData()
        data.add_field('file',
                      BytesIO(audio_bytes),
                      filename=filename,
                      content_type='audio/wav')
        data.add_field('model', 'freya-stt-v1')
        data.add_field('language', 'tr')
        
        start_time = time.time()
        
        async with session.post(
            Config.STT_TRANSCRIPTIONS_URL,
            headers={"Authorization": f"Key {self.fal_key}"},
            data=data,
            timeout=aiohttp.ClientTimeout(total=15)
        ) as response:
            latency = time.time() - start_time
            
            if response.status == 200:
                result = await response.json()
                text = result.get('text', '')
                return text, latency
            else:
                error = await response.text()
                raise Exception(f"STT failed: {response.status} - {error}")
    
    # ===== LLM with Streaming =====
    
    async def generate_response_streaming_async(
        self, 
        user_message: str, 
        conversation_history: list = None
    ) -> AsyncIterator[Tuple[str, bool, dict]]:
        """
        Generate LLM response with streaming (word-by-word)
        Supports multiple providers: fal, openrouter, gemini
        
        Yields:
            Tuple of (text_chunk, is_final, timing_dict)
        """
        # Route to appropriate provider
        if Config.LLM_PROVIDER == 'gemini':
            async for chunk in self._generate_gemini_streaming(user_message, conversation_history):
                yield chunk
        else:
            async for chunk in self._generate_fal_streaming(user_message, conversation_history):
                yield chunk
    
    async def _generate_gemini_streaming(
        self,
        user_message: str,
        conversation_history: list = None
    ) -> AsyncIterator[Tuple[str, bool, dict]]:
        """Generate response using Google Gemini API directly"""
        session = await self.get_session()
        
        # Build conversation history in Gemini format
        contents = []
        if conversation_history:
            for msg in conversation_history:
                contents.append({
                    "role": "user" if msg["role"] == "user" else "model",
                    "parts": [{"text": msg["content"]}]
                })
        
        # Add current message
        contents.append({
            "role": "user",
            "parts": [{"text": user_message}]
        })
        
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": Config.SYSTEM_PROMPT}]
            },
            "generationConfig": {
                "temperature": Config.LLM_TEMPERATURE,
                "maxOutputTokens": Config.LLM_MAX_TOKENS,
                "topP": 0.95,
                "topK": 40
            }
        }
        
        # Gemini streaming endpoint
        url = f"{Config.LLM_BASE_URL}/models/{Config.LLM_MODEL}:streamGenerateContent?alt=sse&key={Config.GEMINI_KEY}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        start_time = time.time()
        first_token_time = None
        accumulated_text = ""
        
        async with session.post(
            url,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"Gemini streaming failed: {response.status} - {error}")
            
            # Read SSE stream
            buffer = ""
            async for chunk in response.content.iter_chunked(8192):
                if not chunk:
                    continue
                
                buffer += chunk.decode('utf-8')
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line or line.startswith(':'):
                        continue
                    
                    if line.startswith('data: '):
                        data_str = line[6:]
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            
                            # Extract text from Gemini response
                            if 'candidates' in data and len(data['candidates']) > 0:
                                candidate = data['candidates'][0]
                                if 'content' in candidate and 'parts' in candidate['content']:
                                    for part in candidate['content']['parts']:
                                        if 'text' in part:
                                            chunk_text = part['text']
                                            
                                            if first_token_time is None and chunk_text:
                                                first_token_time = time.time() - start_time
                                            
                                            # Yield incremental chunk
                                            new_text = chunk_text
                                            if new_text:
                                                accumulated_text += new_text
                                                yield new_text, False, {
                                                    'elapsed': time.time() - start_time,
                                                    'first_token_time': first_token_time
                                                }
                                
                                # Check if finished
                                if candidate.get('finishReason') == 'STOP':
                                    total_time = time.time() - start_time
                                    yield '', True, {
                                        'total_time': total_time,
                                        'first_token_time': first_token_time or total_time
                                    }
                                    return
                        
                        except json.JSONDecodeError:
                            continue
    
    async def _generate_fal_streaming(
        self,
        user_message: str,
        conversation_history: list = None
    ) -> AsyncIterator[Tuple[str, bool, dict]]:
        """Generate response using FAL.AI or OpenRouter"""
        session = await self.get_session()
        
        # Build conversation context
        conversation_context = ""
        if conversation_history:
            for msg in conversation_history:
                if msg["role"] == "user":
                    conversation_context += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    conversation_context += f"Assistant: {msg['content']}\n"
        
        full_prompt = conversation_context + user_message if conversation_context else user_message
        
        payload = {
            "prompt": full_prompt,
            "system_prompt": Config.SYSTEM_PROMPT,
            "model": Config.LLM_MODEL,
            "temperature": Config.LLM_TEMPERATURE,
            "max_tokens": Config.LLM_MAX_TOKENS
        }
        
        headers = {
            "Authorization": f"Key {self.fal_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        start_time = time.time()
        first_token_time = None
        accumulated_text = ""
        
        async with session.post(
            f"{Config.LLM_BASE_URL}/stream",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"LLM streaming failed: {response.status} - {error}")
            
            # Read SSE stream with chunked reading to handle large responses
            buffer = ""
            async for chunk in response.content.iter_chunked(8192):
                if not chunk:
                    continue
                
                buffer += chunk.decode('utf-8')
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line or line.startswith(':'):
                        continue
                    
                    if line.startswith('data: '):
                        data_str = line[6:]  # Remove 'data: ' prefix
                        
                        if data_str == '[DONE]':
                            # Final event
                            total_time = time.time() - start_time
                            yield accumulated_text, True, {
                                'total_time': total_time,
                                'first_token_time': first_token_time
                            }
                            return  # Exit after done
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            
                            # Check for partial output
                            if 'partial' in data and data['partial']:
                                chunk_text = data.get('output', '')
                                
                                if first_token_time is None and chunk_text:
                                    first_token_time = time.time() - start_time
                                
                                # Yield incremental chunk
                                new_text = chunk_text[len(accumulated_text):]
                                if new_text:
                                    accumulated_text = chunk_text
                                    yield new_text, False, {
                                        'elapsed': time.time() - start_time,
                                        'first_token_time': first_token_time
                                    }
                            
                            # Final complete output
                            elif 'output' in data:
                                final_text = data['output']
                                new_text = final_text[len(accumulated_text):]
                                
                                if new_text:
                                    accumulated_text = final_text
                                    total_time = time.time() - start_time
                                    yield new_text, True, {
                                        'total_time': total_time,
                                        'first_token_time': first_token_time or total_time
                                    }
                                return  # Exit after final output
                        
                        except json.JSONDecodeError:
                            continue
    
    # ===== TTS with True Streaming (PCM) =====
    
    async def synthesize_speech_streaming_pcm_async(
        self, 
        text: str,
        speed: float = 1.1
    ) -> AsyncIterator[Tuple[bytes, dict]]:
        """
        Synthesize speech with PCM streaming via SSE
        
        Yields:
            Tuple of (pcm_audio_bytes, metadata)
            metadata contains: {'done': bool, 'inference_time_ms': int, ...}
        """
        session = await self.get_session()
        
        payload = {
            "input": text,
            "voice": "alloy",
            "response_format": "pcm",  # PCM for streaming playback
            "speed": speed
        }
        
        headers = {
            "Authorization": f"Key {self.fal_key}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream"
        }
        
        start_time = time.time()
        first_chunk_time = None
        
        async with session.post(
            f"{Config.TTS_BASE_URL}/stream",
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise Exception(f"TTS streaming failed: {response.status} - {error}")
            
            # Read SSE stream with chunked reading to handle large data
            buffer = ""
            async for chunk in response.content.iter_chunked(8192):
                if not chunk:
                    continue
                
                buffer += chunk.decode('utf-8')
                
                # Process complete lines
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    line = line.strip()
                    
                    if not line or line.startswith(':'):
                        continue
                    
                    if line.startswith('data: '):
                        data_str = line[6:]
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            
                            # Audio chunk
                            if 'audio' in data:
                                audio_b64 = data['audio']
                                pcm_bytes = base64.b64decode(audio_b64)
                                
                                if first_chunk_time is None:
                                    first_chunk_time = time.time() - start_time
                                
                                yield pcm_bytes, {
                                    'done': False,
                                    'ttfb': first_chunk_time,
                                    'elapsed': time.time() - start_time
                                }
                            
                            # Final metadata
                            if data.get('done'):
                                total_time = time.time() - start_time
                                yield b'', {
                                    'done': True,
                                    'ttfb': first_chunk_time or total_time,
                                    'total_time': total_time,
                                    'inference_time_ms': data.get('inference_time_ms', 0),
                                    'audio_duration_sec': data.get('audio_duration_sec', 0)
                                }
                                return  # Exit after final metadata
                        
                        except json.JSONDecodeError:
                            continue
    
    async def close(self):
        """Close sessions"""
        if self._session and not self._session.closed:
            await self._session.close()
        
        if self._requests_session:
            self._requests_session.close()
    
    def __del__(self):
        """Cleanup"""
        if self._requests_session:
            self._requests_session.close()

"""
Optimized Voice Services with Async/Streaming Support
"""
import requests
import aiohttp
import asyncio
from typing import Optional, AsyncIterator
from pathlib import Path
from config import Config


class VoiceServices:
    """High-performance voice services with streaming and connection pooling"""
    
    def __init__(self):
        self.fal_key = Config.FAL_KEY
        self.openrouter_key = Config.OPENROUTER_KEY
        
        # Persistent session for better performance (connection pooling)
        self._session = None
        self._requests_session = None
    
    async def get_session(self) -> aiohttp.ClientSession:
        """Get or create persistent aiohttp session with connection pooling"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            connector = aiohttp.TCPConnector(
                limit=10,              # Max concurrent connections
                limit_per_host=5,      # Max connections per host
                ttl_dns_cache=300      # DNS cache TTL (5 minutes)
            )
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector
            )
        return self._session
    
    def get_requests_session(self) -> requests.Session:
        """Get or create persistent requests session"""
        if self._requests_session is None:
            self._requests_session = requests.Session()
            # Configure connection pooling
            adapter = requests.adapters.HTTPAdapter(
                pool_connections=10,
                pool_maxsize=10,
                max_retries=3
            )
            self._requests_session.mount('http://', adapter)
            self._requests_session.mount('https://', adapter)
        return self._requests_session
    
    async def close(self):
        """Close persistent sessions"""
        if self._session and not self._session.closed:
            await self._session.close()
        if self._requests_session:
            self._requests_session.close()
    
    # ===== STT (Speech-to-Text) =====
    
    def transcribe_audio(self, audio_file: str) -> str:
        """Transcribe audio to text (synchronous)"""
        session = self.get_requests_session()
        
        with open(audio_file, 'rb') as f:
            response = session.post(
                Config.STT_TRANSCRIBE_URL,
                headers={"Authorization": f"Key {self.fal_key}"},
                files={'file': (Path(audio_file).name, f, 'audio/wav')},
                data={'model': 'freya-stt-v1', 'language': 'tr'},
                timeout=Config.STT_TIMEOUT
            )
        
        if response.status_code == 200:
            return response.json().get('text', '')
        else:
            raise Exception(f"STT failed: {response.status_code} - {response.text}")
    
    async def transcribe_audio_async(self, audio_file: str) -> str:
        """Transcribe audio to text (asynchronous with connection pooling)"""
        session = await self.get_session()
        
        with open(audio_file, 'rb') as f:
            form = aiohttp.FormData()
            form.add_field('file', f, filename=Path(audio_file).name, content_type='audio/wav')
            form.add_field('model', 'freya-stt-v1')
            form.add_field('language', 'tr')
            
            async with session.post(
                Config.STT_TRANSCRIBE_URL,
                headers={"Authorization": f"Key {self.fal_key}"},
                data=form,
                timeout=aiohttp.ClientTimeout(total=Config.STT_TIMEOUT)
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get('text', '')
                else:
                    text = await response.text()
                    raise Exception(f"STT failed: {response.status} - {text}")
    
    # ===== LLM (Language Model) =====
    
    def generate_response(self, user_message: str, conversation_history: list = None) -> str:
        """Generate LLM response (synchronous)"""
        session = self.get_requests_session()
        
        # Prepare request based on whether using FAL's OpenRouter or direct
        if Config.USE_FAL_OPENROUTER:
            # FAL.AI's OpenRouter format (uses prompt + system_prompt, not messages)
            headers = {
                "Authorization": f"Key {self.fal_key}",
                "Content-Type": "application/json"
            }
            
            # Build conversation context from history
            conversation_context = ""
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        conversation_context += f"User: {msg['content']}\n"
                    elif msg["role"] == "assistant":
                        conversation_context += f"Assistant: {msg['content']}\n"
            
            # Combine context with current message
            full_prompt = conversation_context + user_message if conversation_context else user_message
            
            payload = {
                "prompt": full_prompt,
                "system_prompt": Config.SYSTEM_PROMPT,
                "model": Config.LLM_MODEL,
                "temperature": Config.LLM_TEMPERATURE,
                "max_tokens": Config.LLM_MAX_TOKENS
            }
        else:
            # Direct OpenRouter format (uses messages array)
            messages = []
            if conversation_history:
                messages = conversation_history.copy()
            else:
                messages.append({"role": "system", "content": Config.SYSTEM_PROMPT})
            messages.append({"role": "user", "content": user_message})
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": Config.LLM_MODEL,
                "messages": messages,
                "temperature": Config.LLM_TEMPERATURE,
                "max_tokens": Config.LLM_MAX_TOKENS
            }
        
        response = session.post(
            Config.LLM_URL,
            headers=headers,
            json=payload,
            timeout=Config.LLM_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            # FAL's OpenRouter returns "output", standard OpenRouter returns "choices"
            if Config.USE_FAL_OPENROUTER:
                return result.get('output', '')
            else:
                return result['choices'][0]['message']['content']
        else:
            raise Exception(f"LLM failed: {response.status_code} - {response.text}")
    
    async def generate_response_async(self, user_message: str, conversation_history: list = None) -> str:
        """Generate LLM response (asynchronous with connection pooling)"""
        session = await self.get_session()
        
        # Prepare request based on whether using FAL's OpenRouter or direct
        if Config.USE_FAL_OPENROUTER:
            # FAL.AI's OpenRouter format (uses prompt + system_prompt, not messages)
            headers = {
                "Authorization": f"Key {self.fal_key}",
                "Content-Type": "application/json"
            }
            
            # Build conversation context from history
            conversation_context = ""
            if conversation_history:
                for msg in conversation_history:
                    if msg["role"] == "user":
                        conversation_context += f"User: {msg['content']}\n"
                    elif msg["role"] == "assistant":
                        conversation_context += f"Assistant: {msg['content']}\n"
            
            # Combine context with current message
            full_prompt = conversation_context + user_message if conversation_context else user_message
            
            payload = {
                "prompt": full_prompt,
                "system_prompt": Config.SYSTEM_PROMPT,
                "model": Config.LLM_MODEL,
                "temperature": Config.LLM_TEMPERATURE,
                "max_tokens": Config.LLM_MAX_TOKENS
            }
        else:
            # Direct OpenRouter format (uses messages array)
            messages = []
            if conversation_history:
                messages = conversation_history.copy()
            else:
                messages.append({"role": "system", "content": Config.SYSTEM_PROMPT})
            messages.append({"role": "user", "content": user_message})
            
            headers = {
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": Config.LLM_MODEL,
                "messages": messages,
                "temperature": Config.LLM_TEMPERATURE,
                "max_tokens": Config.LLM_MAX_TOKENS
            }
        
        async with session.post(
            Config.LLM_URL,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=Config.LLM_TIMEOUT)
        ) as response:
            if response.status == 200:
                result = await response.json()
                # FAL's OpenRouter returns "output", standard OpenRouter returns "choices"
                if Config.USE_FAL_OPENROUTER:
                    return result.get('output', '')
                else:
                    return result['choices'][0]['message']['content']
            else:
                text = await response.text()
                raise Exception(f"LLM failed: {response.status} - {text}")
    
    # ===== TTS (Text-to-Speech) =====
    
    def synthesize_speech(self, text: str, output_file: Optional[str] = None) -> str:
        """Synthesize speech (synchronous, non-streaming)"""
        session = self.get_requests_session()
        
        response = session.post(
            Config.TTS_SPEECH_URL,
            headers={
                "Authorization": f"Key {self.fal_key}",
                "Content-Type": "application/json"
            },
            json={
                "input": text,
                "model": "freya-tts-tr1",
                "response_format": Config.AUDIO_FORMAT,
                "speed": 1.0
            },
            timeout=Config.TTS_TIMEOUT
        )
        
        if response.status_code == 200:
            if not output_file:
                import time
                output_file = Config.OUTPUT_DIR / f"response_{int(time.time())}.mp3"
            
            Path(output_file).write_bytes(response.content)
            return str(output_file)
        else:
            raise Exception(f"TTS failed: {response.status_code} - {response.text}")
    
    def synthesize_speech_streaming(self, text: str, output_file: Optional[str] = None):
        """Synthesize speech with streaming (synchronous)"""
        session = self.get_requests_session()
        
        response = session.post(
            Config.TTS_STREAM_URL,
            headers={
                "Authorization": f"Key {self.fal_key}",
                "Content-Type": "application/json"
            },
            json={
                "input": text,
                "response_format": Config.AUDIO_FORMAT
            },
            stream=True,
            timeout=Config.TTS_TIMEOUT
        )
        
        if response.status_code == 200:
            audio_chunks = []
            
            for chunk in response.iter_content(chunk_size=Config.CHUNK_SIZE):
                if chunk:
                    audio_chunks.append(chunk)
                    yield chunk  # Stream chunk for immediate playback
            
            # Save complete audio if needed
            if output_file:
                Path(output_file).write_bytes(b''.join(audio_chunks))
        else:
            raise Exception(f"TTS streaming failed: {response.status_code}")
    
    async def synthesize_speech_async(self, text: str, output_file: Optional[str] = None) -> bytes:
        """Synthesize speech (asynchronous with connection pooling)"""
        session = await self.get_session()
        
        async with session.post(
            Config.TTS_SPEECH_URL,
            headers={
                "Authorization": f"Key {self.fal_key}",
                "Content-Type": "application/json"
            },
            json={
                "input": text,
                "response_format": Config.AUDIO_FORMAT
            },
            timeout=aiohttp.ClientTimeout(total=Config.TTS_TIMEOUT)
        ) as response:
            if response.status == 200:
                audio_data = await response.read()
                
                if output_file:
                    Path(output_file).write_bytes(audio_data)
                
                return audio_data
            else:
                text = await response.text()
                raise Exception(f"TTS failed: {response.status} - {text}")
    
    async def synthesize_speech_streaming_async(self, text: str):
        """
        Synthesize speech with async streaming (lowest latency)
        Yields audio chunks as they arrive from the API for immediate playback
        """
        session = await self.get_session()
        
        async with session.post(
            Config.TTS_STREAM_URL,
            headers={
                "Authorization": f"Key {self.fal_key}",
                "Content-Type": "application/json"
            },
            json={
                "input": text,
                "response_format": Config.AUDIO_FORMAT
            },
            timeout=aiohttp.ClientTimeout(total=Config.TTS_TIMEOUT)
        ) as response:
            if response.status == 200:
                # Yield chunks as they arrive for immediate playback
                async for chunk in response.content.iter_chunked(Config.CHUNK_SIZE):
                    if chunk:
                        yield chunk
            else:
                error_text = await response.text()
                raise Exception(f"TTS streaming failed: {response.status} - {error_text}")
    
    def __del__(self):
        """Cleanup when object is destroyed"""
        if self._requests_session:
            self._requests_session.close()

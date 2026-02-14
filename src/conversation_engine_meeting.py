"""
Meeting Conversation Engine for Recall.ai Integration
- Adapted from conversation_engine_optimized.py
- Text input (no audio recording, no STT)
- Audio output to Recall bot (not local speakers)
- Keeps: sentence chunking, parallel TTS, streaming
"""
import asyncio
import time
import sys
import os
from typing import Dict, List, Any

# Add parent directory to path
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'bot-orchestrator'))

from voice_services_optimized import VoiceServicesOptimized
from config import Config
from recall_api import RecallAPIClient


class MeetingConversationEngine:
    """Conversation engine adapted for Recall.ai meeting bots"""
    
    def __init__(self, redis_queue=None):
        self.services = VoiceServicesOptimized()
        self.recall_client = RecallAPIClient()
        self.redis_queue = redis_queue  # Persistent Redis connection for audio publishing
        
        # Audio queue for sequential upload without blocking generation
        self.audio_queues = {}  # bot_id -> asyncio.Queue
        self.upload_tasks = {}  # bot_id -> Task
        
        # Cancellation flags for barge-in
        self._cancel_flags = {}  # bot_id -> asyncio.Event
        
        # Timing tracking
        self.first_audio_times = {}  # bot_id -> timestamp
        self.turn_start_times = {}   # bot_id -> timestamp
    
    def cancel_response(self, bot_id: str):
        """
        Cancel current response for barge-in
        
        This sets a cancellation flag that stops:
        - New TTS tasks from starting
        - Pending TTS tasks (via cancel())
        - Audio upload worker from sending new chunks
        
        Note: Already-uploaded chunks cannot be recalled
        """
        if bot_id not in self._cancel_flags:
            self._cancel_flags[bot_id] = asyncio.Event()
        
        self._cancel_flags[bot_id].set()
        print(f"🛑 Cancellation requested for bot {bot_id}")
    
    def _is_cancelled(self, bot_id: str) -> bool:
        """Check if response for this bot has been cancelled"""
        if bot_id in self._cancel_flags:
            return self._cancel_flags[bot_id].is_set()
        return False
    
    def _clear_cancellation(self, bot_id: str):
        """Clear cancellation flag for new response"""
        if bot_id in self._cancel_flags:
            self._cancel_flags[bot_id].clear()
    
    async def process_text_to_audio(
        self,
        text: str,
        bot_id: str,
        history: List[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Process text input and generate audio output for meeting bot
        
        Pipeline:
        1. LLM streaming (text -> text)
        2. Sentence chunking (intelligent text splitting)
        3. Parallel TTS (text -> PCM audio)
        4. Audio upload to Recall bot (PCM -> meeting)
        
        Args:
            text: User utterance text (from Recall transcript)
            bot_id: Recall bot identifier
            history: Conversation history
        
        Returns:
            dict with detailed metrics
        """
        metrics = {
            'llm': {},
            'tts': {},
            'total': {},
            'response_text': ''
        }
        
        total_start = time.time()
        self.turn_start_times[bot_id] = total_start
        self.first_audio_times[bot_id] = None
        
        # Clear any previous cancellation
        self._clear_cancellation(bot_id)
        
        print(f"\n{'='*70}")
        print(f"🧠 [CONVERSATION ENGINE] Starting pipeline")
        print(f"   Bot ID: {bot_id[:8]}...")
        print(f"   User input: {text}")
        print(f"   History length: {len(history or [])} messages")
        print(f"{'='*70}")
        
        # === LLM Streaming + Chunked TTS ===
        llm_start = time.time()
        
        print(f"\n🤖 [LLM] Requesting response...")
        print(f"🤖 [LLM] System prompt length: {len(Config.SYSTEM_PROMPT)} chars")
        print(f"🤖 [LLM] User utterance: '{text}'")
        print(f"🤖 [LLM] History messages: {len(history or [])}")
        
        # Start LLM streaming
        llm_stream = self.services.generate_response_streaming_async(
            text,
            history or []
        )
        
        # Initialize audio queue for this bot
        if bot_id not in self.audio_queues:
            self.audio_queues[bot_id] = asyncio.Queue()
        
        # Start upload worker if not running
        if bot_id not in self.upload_tasks or self.upload_tasks[bot_id].done():
            self.upload_tasks[bot_id] = asyncio.create_task(
                self._audio_uploader_worker(bot_id)
            )
        
        # Track TTS calls and tasks
        tts_calls = []
        tts_generation_tasks = []
        accumulated_text = ""
        full_response = ""
        
        # Configuration for sentence-level chunking (from conversation_engine_optimized.py)
        MIN_CHUNK_CHARS = Config.TTS_CHUNK_MIN_CHARS  # 20 chars
        MAX_CHUNK_CHARS = Config.TTS_CHUNK_MAX_CHARS  # 100 chars
        SENTENCE_DELIMITERS = ['. ', '! ', '? ', '.\n', '!\n', '?\n', '. "', '! "', '? "']
        CLAUSE_DELIMITERS = [', ', '; ', ': ', ' - ', ' – ']
        WORD_DELIMITERS = [' ve ', ' ama ', ' çünkü ', ' ancak ']
        
        first_token_time = None
        
        print(f"   🔄 [LLM] Streaming response...")
        
        # Process LLM stream
        async for chunk_text, is_final, timing in llm_stream:
            # Check cancellation
            if self._is_cancelled(bot_id):
                print(f"   ⏹️  LLM streaming cancelled")
                break
            
            if first_token_time is None and chunk_text:
                first_token_time = time.time() - llm_start
                print(f"   🎯 First LLM token: {first_token_time*1000:.0f}ms")
            
            accumulated_text += chunk_text
            full_response += chunk_text
            
            # Intelligent chunking logic (from conversation_engine_optimized.py)
            chunk_to_send = None
            chunk_length = len(accumulated_text)
            
            # Strategy 1: Find sentence boundaries
            if chunk_length >= MIN_CHUNK_CHARS:
                best_split_pos = -1
                best_delimiter = None
                
                for delimiter in SENTENCE_DELIMITERS:
                    pos = accumulated_text.rfind(delimiter)
                    if pos > best_split_pos and pos >= MIN_CHUNK_CHARS - len(delimiter):
                        best_split_pos = pos
                        best_delimiter = delimiter
                
                # Strategy 2: Try clause boundaries
                if best_split_pos == -1 and chunk_length >= MIN_CHUNK_CHARS * 1.5:
                    for delimiter in CLAUSE_DELIMITERS:
                        pos = accumulated_text.rfind(delimiter)
                        if pos > best_split_pos and pos >= MIN_CHUNK_CHARS - len(delimiter):
                            best_split_pos = pos
                            best_delimiter = delimiter
                
                # Strategy 3: Try word boundaries
                if best_split_pos == -1 and chunk_length >= MIN_CHUNK_CHARS * 2:
                    for delimiter in WORD_DELIMITERS:
                        pos = accumulated_text.rfind(delimiter)
                        if pos > best_split_pos and pos >= MIN_CHUNK_CHARS - len(delimiter):
                            best_split_pos = pos
                            best_delimiter = delimiter
                
                # Split at delimiter
                if best_split_pos > -1 and best_delimiter:
                    split_end = best_split_pos + len(best_delimiter)
                    chunk_to_send = accumulated_text[:split_end].strip()
                    accumulated_text = accumulated_text[split_end:]
            
            # Strategy 4: Force send if too long
            if not chunk_to_send and chunk_length >= MAX_CHUNK_CHARS:
                last_space = accumulated_text.rfind(' ', 0, MAX_CHUNK_CHARS)
                if last_space > MIN_CHUNK_CHARS:
                    chunk_to_send = accumulated_text[:last_space].strip()
                    accumulated_text = accumulated_text[last_space:].strip()
                else:
                    chunk_to_send = accumulated_text.strip()
                    accumulated_text = ""
            
            # Strategy 5: Send on is_final
            if not chunk_to_send and is_final and accumulated_text.strip():
                chunk_to_send = accumulated_text.strip()
                accumulated_text = ""
            
            # Fire TTS for this chunk
            if chunk_to_send:
                # Check cancellation before firing TTS
                if self._is_cancelled(bot_id):
                    print(f"   ⏹️  Skipping TTS chunk (cancelled)")
                    break
                
                chunk_id = len(tts_calls) + 1
                tts_speed = self._get_chunk_speed(chunk_id)
                
                print(f"   🔊 Firing TTS chunk #{chunk_id}: \"{chunk_to_send[:50]}...\" ({len(chunk_to_send)} chars, speed={tts_speed:.2f}x)")
                
                # Create task to generate TTS
                tts_task = asyncio.create_task(
                    self._generate_tts_to_queue(
                        text=chunk_to_send,
                        chunk_num=chunk_id,
                        bot_id=bot_id,
                        total_start_time=total_start,
                        speed=tts_speed
                    )
                )
                tts_generation_tasks.append(tts_task)
                tts_calls.append({'chunk_id': chunk_id, 'text': chunk_to_send})
            
            if is_final:
                break
        
        # Handle remaining text
        if accumulated_text.strip() and not self._is_cancelled(bot_id):
            chunk_id = len(tts_calls) + 1
            tts_speed = self._get_chunk_speed(chunk_id)
            print(f"   🔊 Final TTS chunk: \"{accumulated_text.strip()[:40]}...\" ({len(accumulated_text.strip())} chars)")
            
            tts_task = asyncio.create_task(
                self._generate_tts_to_queue(
                    text=accumulated_text.strip(),
                    chunk_num=chunk_id,
                    bot_id=bot_id,
                    total_start_time=total_start,
                    speed=tts_speed
                )
            )
            tts_generation_tasks.append(tts_task)
            tts_calls.append({'chunk_id': chunk_id, 'text': accumulated_text.strip()})
            full_response += accumulated_text
        
        # Wait for all TTS generation tasks
        if tts_generation_tasks:
            print(f"\n🎵 [TTS] Waiting for {len(tts_generation_tasks)} TTS tasks to complete...")
            tts_results = await asyncio.gather(*tts_generation_tasks, return_exceptions=True)
            for i, result in enumerate(tts_results):
                if isinstance(result, Exception):
                    print(f"   ⚠️  TTS chunk {i+1} failed: {result}")
                    tts_calls[i]['error'] = str(result)
                elif isinstance(result, dict):
                    tts_calls[i].update(result)
                    audio_bytes = result.get('total_bytes', 0)
                    print(f"   ✅ TTS chunk {i+1}: {audio_bytes} bytes generated")
        
        # Signal end of audio queue
        await self.audio_queues[bot_id].put(None)
        
        # Wait for upload to complete (with timeout)
        try:
            await asyncio.wait_for(self.upload_tasks[bot_id], timeout=30.0)
        except asyncio.TimeoutError:
            print("   ⚠️  Audio upload timed out")
        
        # Calculate metrics
        total_time = time.time() - total_start
        
        metrics['llm'] = {
            'first_token_time': first_token_time or 0,
            'total_time': time.time() - llm_start
        }
        
        metrics['tts'] = {
            'calls': len(tts_calls),
            'details': tts_calls,
            'total_time': total_time
        }
        
        metrics['response_text'] = full_response.strip()
        
        # Calculate TTFA
        if self.first_audio_times.get(bot_id):
            ttfa_from_start = self.first_audio_times[bot_id] - self.turn_start_times[bot_id]
            metrics['total']['ttfa'] = ttfa_from_start
        else:
            metrics['total']['ttfa'] = 0
        
        metrics['total']['time'] = total_time
        
        return metrics
    
    def _get_chunk_speed(self, chunk_num: int) -> float:
        """Calculate TTS speed with progressive ramping (from conversation_engine_optimized.py)"""
        if not Config.ENABLE_SPEED_RAMPING:
            return Config.TTS_SPEED
        
        if chunk_num <= Config.TTS_SPEED_RAMP_CHUNKS:
            progress = (chunk_num - 1) / max(1, Config.TTS_SPEED_RAMP_CHUNKS - 1)
            speed = Config.TTS_SPEED_INITIAL + (Config.TTS_SPEED - Config.TTS_SPEED_INITIAL) * progress
            return speed
        else:
            return Config.TTS_SPEED
    
    async def _generate_tts_to_queue(
        self,
        text: str,
        chunk_num: int,
        bot_id: str,
        total_start_time: float,
        speed: float = None
    ) -> dict:
        """Generate TTS and stream to audio queue (adapted from conversation_engine_optimized.py)"""
        if speed is None:
            speed = Config.TTS_SPEED
        
        tts_start = time.time()
        chunk_audio_queue = None
        
        try:
            # Check cancellation
            if self._is_cancelled(bot_id):
                return {'chunk_num': chunk_num, 'cancelled': True}
            
            # Generate TTS stream
            tts_stream = self.services.synthesize_speech_streaming_pcm_async(
                text,
                speed=speed
            )
            
            # Create queue for this chunk's audio bytes
            chunk_audio_queue = asyncio.Queue()
            
            # Add chunk metadata to main queue
            await self.audio_queues[bot_id].put({
                'type': 'start_chunk',
                'audio_queue': chunk_audio_queue,
                'chunk_num': chunk_num,
                'text': text,
                'start_time': tts_start
            })
            
            # Stream audio bytes
            first_byte_time = None
            byte_count = 0
            
            async for audio_data in tts_stream:
                # Check cancellation
                if self._is_cancelled(bot_id):
                    await chunk_audio_queue.put(None)
                    return {'chunk_num': chunk_num, 'cancelled': True}
                
                if isinstance(audio_data, tuple):
                    audio_bytes, metadata = audio_data
                    if metadata.get('done'):
                        break
                else:
                    audio_bytes = audio_data
                
                if not audio_bytes:
                    continue
                
                if first_byte_time is None:
                    first_byte_time = time.time() - tts_start
                
                await chunk_audio_queue.put(audio_bytes)
                byte_count += len(audio_bytes)
            
            # Signal end of chunk
            await chunk_audio_queue.put(None)
            
            generation_time = time.time() - tts_start
            
            # Log TTS validation
            print(f"🎵 [TTS] Chunk #{chunk_num}: bytes={byte_count} sr=16000 ch=1", flush=True)
            
            return {
                'chunk_num': chunk_num,
                'generation_time': generation_time,
                'start_time': tts_start,
                'total_bytes': byte_count,
                'ttfb': first_byte_time,
                'bytes': byte_count
            }
        
        except Exception as e:
            print(f"   ⚠️  TTS generation for chunk {chunk_num} failed: {e}")
            if chunk_audio_queue is not None:
                try:
                    await chunk_audio_queue.put(None)
                except:
                    pass
            return {
                'chunk_num': chunk_num,
                'error': str(e),
                'start_time': tts_start
            }
    
    async def _audio_uploader_worker(self, bot_id: str):
        """
        Worker that uploads audio chunks to Recall bot
        
        Replaces _playback_worker from conversation_engine_optimized.py
        Instead of PyAudio stream.write(), we POST audio to Recall API
        """
        try:
            while True:
                # Check cancellation
                if self._is_cancelled(bot_id):
                    print(f"   ⏹️  Upload worker cancelled for bot {bot_id}")
                    # Drain remaining items
                    while not self.audio_queues[bot_id].empty():
                        try:
                            self.audio_queues[bot_id].get_nowait()
                        except:
                            break
                    break
                
                # Get next audio chunk metadata
                audio_item = await self.audio_queues[bot_id].get()
                
                # None signals end of audio
                if audio_item is None:
                    self.audio_queues[bot_id].task_done()
                    break
                
                if audio_item.get('type') == 'start_chunk':
                    chunk_num = audio_item['chunk_num']
                    chunk_audio_queue = audio_item['audio_queue']
                    
                    print(f"   📤 Uploading audio chunk #{chunk_num} to Recall bot")
                    
                    chunk_start = time.time()
                    ttfa = None
                    bytes_uploaded = 0
                    
                    # Stream audio bytes to Recall
                    try:
                        while True:
                            # Check cancellation
                            if self._is_cancelled(bot_id):
                                print(f"   ⏹️  Upload cancelled for chunk #{chunk_num}")
                                break
                            
                            audio_data = await chunk_audio_queue.get()
                            if audio_data is None:
                                break
                            
                            if isinstance(audio_data, tuple):
                                audio_bytes = audio_data[0]
                            else:
                                audio_bytes = audio_data
                            
                            if not audio_bytes:
                                continue
                            
                            # Validate TTS audio quality
                            import struct
                            if len(audio_bytes) >= 2:
                                samples = struct.unpack("<" + "h" * (len(audio_bytes) // 2), audio_bytes)
                                peak = max(abs(x) for x in samples) if samples else 0
                                print(f"   🎵 [TTS-VALIDATE] bytes={len(audio_bytes)} peak={peak}", flush=True)
                                if peak < 200:
                                    print(f"   ⚠️  [TTS-VALIDATE] Very low audio peak - may be silence!", flush=True)
                            
                            # Record TTFA
                            if ttfa is None:
                                ttfa = time.time() - chunk_start
                                
                                if self.first_audio_times.get(bot_id) is None:
                                    self.first_audio_times[bot_id] = time.time()
                                    actual_ttfa = (self.first_audio_times[bot_id] - self.turn_start_times[bot_id]) * 1000
                                    print(f"   🔊 TTFA: {actual_ttfa:.0f}ms (Time To First Audio)")
                            
                            # Publish audio to Redis for Output Media
                            try:
                                # Use persistent RedisQueue instance (passed in constructor)
                                # This avoids creating new connections for every chunk (MUCH more efficient)
                                if self.redis_queue:
                                    await self.redis_queue.publish_audio_output(bot_id, audio_bytes)
                                    bytes_uploaded += len(audio_bytes)
                                else:
                                    # Fallback: create temporary instance (slow path)
                                    print(f"   ⚠️  No persistent RedisQueue, creating temporary instance (slower)", flush=True)
                                    from redis_queue import RedisQueue
                                    temp_queue = RedisQueue()
                                    await temp_queue.connect()
                                    await temp_queue.publish_audio_output(bot_id, audio_bytes)
                                    await temp_queue.close()
                                    bytes_uploaded += len(audio_bytes)
                            except Exception as e:
                                print(f"   ⚠️  Failed to publish audio chunk: {e}")
                                # Continue with next chunk
                                break
                        
                        chunk_time = time.time() - chunk_start
                        print(f"   ✅ Chunk #{chunk_num} uploaded: {bytes_uploaded} bytes in {chunk_time*1000:.0f}ms")
                    
                    except Exception as e:
                        print(f"   ⚠️  Error uploading chunk #{chunk_num}: {e}")
                
                self.audio_queues[bot_id].task_done()
        
        except Exception as e:
            print(f"❌ Upload worker error for bot {bot_id}: {e}")
        
        finally:
            print(f"   🏁 Upload worker finished for bot {bot_id}")

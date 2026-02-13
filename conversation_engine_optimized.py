"""
Ultra-Optimized Conversation Engine
- LLM streams → immediate chunked TTS
- Filler audio while waiting for LLM
- True real-time PCM playback
- Detailed TTFA/TTFB metrics
"""
import asyncio
import time
from typing import Tuple, Dict
from voice_services_optimized import VoiceServicesOptimized
from audio_recorder_optimized import AudioRecorderOptimized
from audio_player_optimized import AudioPlayerOptimized
from config import Config


class ConversationEngineOptimized:
    """Ultra-low-latency conversation engine"""
    
    def __init__(self):
        self.services = VoiceServicesOptimized()
        self.recorder = AudioRecorderOptimized()
        self.player = AudioPlayerOptimized()
        self.conversation_history = []
        
        # Audio queue for sequential playback without blocking generation
        self.audio_queue = asyncio.Queue()
        self.playback_task = None
        
        # Global timing for TTFA tracking
        self.first_audio_time = None  # Track when first audio actually plays
        self.turn_start_time = None   # Track start of entire turn
        
        # Filler phrases for thinking time
        self.filler_phrases = [
            "Hmm,",
            "Bir saniye,",
            "Düşüneyim,",
            "Anlıyorum,"
        ]
    
    async def process_turn_ultra_optimized(
        self,
        audio_bytes: bytes = None,
        use_filler: bool = True
    ) -> Dict:
        """
        Process conversation turn with maximum optimization
        
        Strategy:
        1. STT from memory (no disk I/O)
        2. Fire filler TTS immediately (if LLM takes >200ms)
        3. Stream LLM response, chunk to TTS when >=15 tokens
        4. Play TTS chunks in real-time as PCM streams arrive
        
        Returns:
            dict with detailed metrics
        """
        metrics = {
            'stt': {},
            'llm': {},
            'tts': {},
            'total': {}
        }
        
        total_start = time.time()
        self.turn_start_time = total_start  # Track for global TTFA
        self.first_audio_time = None  # Reset for this turn
        
        # === STEP 1: STT (In-Memory) ===
        print("\n" + "="*60)
        print("🎧 Step 1: Speech-to-Text (In-Memory)")
        print("="*60)
        
        stt_start = time.time()
        user_text, stt_latency = await self.services.transcribe_audio_bytes_async(audio_bytes)
        metrics['stt'] = {
            'latency': stt_latency,
            'text': user_text
        }
        
        print(f"👤 User: {user_text}")
        print(f"   ⏱️  STT: {stt_latency*1000:.0f}ms")
        
        # === STEP 2: LLM Streaming + Chunked TTS ===
        print("\n" + "="*60)
        print("🤖 Step 2: LLM Streaming → Chunked TTS")
        print("="*60)
        
        llm_start = time.time()
        
        # Start LLM streaming
        llm_stream = self.services.generate_response_streaming_async(
            user_text,
            self.conversation_history
        )
        
        # Track LLM chunks and TTS calls
        llm_chunks = []
        tts_calls = []
        tts_generation_tasks = []  # Track TTS generation (separate from playback)
        accumulated_text = ""
        filler_task = None
        filler_cancelled = False
        
        # Start playback worker if not running
        if self.playback_task is None or self.playback_task.done():
            self.playback_task = asyncio.create_task(self._playback_worker())
        
        # Configuration for sentence-level chunking (ULTRA-AGGRESSIVE)
        MIN_CHUNK_CHARS = Config.TTS_CHUNK_MIN_CHARS  # Very low (20 chars)
        MAX_CHUNK_CHARS = Config.TTS_CHUNK_MAX_CHARS  # Force early (100 chars)
        SENTENCE_DELIMITERS = ['. ', '! ', '? ', '.\n', '!\n', '?\n', '. "', '! "', '? "']  # Include quotes
        CLAUSE_DELIMITERS = [', ', '; ', ': ', ' - ', ' – ']  # More break points
        WORD_DELIMITERS = [' ve ', ' ama ', ' çünkü ', ' ancak ']  # Turkish conjunctions
        
        # Fire filler audio in parallel
        if use_filler:
            filler_task = asyncio.create_task(self._play_filler())
        
        first_token_time = None
        
        # Process LLM stream
        async for chunk_text, is_final, timing in llm_stream:
            if first_token_time is None and chunk_text:
                first_token_time = time.time() - llm_start
                print(f"   🎯 First LLM token: {first_token_time*1000:.0f}ms")
                
                # Cancel filler if LLM is fast
                if filler_task and not filler_task.done():
                    filler_task.cancel()
                    filler_cancelled = True
                    print("   ⏸️  Filler cancelled (LLM fast)")
            
            accumulated_text += chunk_text
            llm_chunks.append(chunk_text)
            
            # Check if we should fire TTS for this accumulated text (INTELLIGENT CHUNKING)
            chunk_to_send = None
            chunk_length = len(accumulated_text)
            
            # Strategy 1: Find sentence boundaries (highest priority)
            if chunk_length >= MIN_CHUNK_CHARS:
                # Look for sentence delimiters in the accumulated text
                best_split_pos = -1
                best_delimiter = None
                
                for delimiter in SENTENCE_DELIMITERS:
                    pos = accumulated_text.rfind(delimiter)  # Find LAST occurrence
                    if pos > best_split_pos and pos >= MIN_CHUNK_CHARS - len(delimiter):
                        best_split_pos = pos
                        best_delimiter = delimiter
                
                # Strategy 2: Try clause boundaries if no sentence found
                if best_split_pos == -1 and chunk_length >= MIN_CHUNK_CHARS * 1.5:
                    for delimiter in CLAUSE_DELIMITERS:
                        pos = accumulated_text.rfind(delimiter)
                        if pos > best_split_pos and pos >= MIN_CHUNK_CHARS - len(delimiter):
                            best_split_pos = pos
                            best_delimiter = delimiter
                
                # Strategy 3: Try word boundaries if getting longer
                if best_split_pos == -1 and chunk_length >= MIN_CHUNK_CHARS * 2:
                    for delimiter in WORD_DELIMITERS:
                        pos = accumulated_text.rfind(delimiter)
                        if pos > best_split_pos and pos >= MIN_CHUNK_CHARS - len(delimiter):
                            best_split_pos = pos
                            best_delimiter = delimiter
                
                # If we found a good split point, send everything up to it
                if best_split_pos > -1 and best_delimiter:
                    split_end = best_split_pos + len(best_delimiter)
                    chunk_to_send = accumulated_text[:split_end].strip()
                    accumulated_text = accumulated_text[split_end:]  # Keep remainder
                    print(f"   ✂️  Found delimiter '{best_delimiter.strip()}' at pos {best_split_pos}, splitting chunk")
            
            # Strategy 4: FORCE send if exceeding max (prevent accumulation)
            if not chunk_to_send and chunk_length >= MAX_CHUNK_CHARS:
                # Find last space to avoid mid-word split
                last_space = accumulated_text.rfind(' ', 0, MAX_CHUNK_CHARS)
                if last_space > MIN_CHUNK_CHARS:
                    chunk_to_send = accumulated_text[:last_space].strip()
                    accumulated_text = accumulated_text[last_space:].strip()
                else:
                    chunk_to_send = accumulated_text.strip()
                    accumulated_text = ""
                print(f"   ⚠️  Forcing TTS fire at {chunk_length} chars (max: {MAX_CHUNK_CHARS})")
            
            # Strategy 5: Send on is_final even if short (ensure we don't lose last chunk)
            if not chunk_to_send and is_final and accumulated_text.strip():
                chunk_to_send = accumulated_text.strip()
                accumulated_text = ""
            
            # Fire TTS for this chunk
            if chunk_to_send:
                chunk_id = len(tts_calls) + 1
                
                # Calculate progressive speed for this chunk (slower initial chunks)
                tts_speed = self._get_chunk_speed(chunk_id)
                
                print(f"   🔊 Firing TTS chunk #{chunk_id}: \"{chunk_to_send[:50]}...\" ({len(chunk_to_send)} chars, speed={tts_speed:.2f}x)")
                
                # Create task to generate TTS (non-blocking)
                tts_task = asyncio.create_task(
                    self._generate_tts_to_queue(chunk_to_send, chunk_id, total_start, tts_speed)
                )
                tts_generation_tasks.append(tts_task)
                tts_calls.append({'chunk_id': chunk_id, 'text': chunk_to_send})
            
            # Debug: Log accumulation progress
            elif chunk_length > 0 and chunk_length % 30 == 0:
                print(f"   📝 Accumulated: {chunk_length} chars, waiting for delimiter...")
            
            if is_final:
                break
        
        # === Handle remaining text ===
        if accumulated_text.strip():
            chunk_id = len(tts_calls) + 1
            tts_speed = self._get_chunk_speed(chunk_id)
            print(f"   🔊 Final TTS chunk: \"{accumulated_text.strip()[:40]}...\" ({len(accumulated_text.strip())} chars, speed={tts_speed:.2f}x)")
            
            tts_task = asyncio.create_task(
                self._generate_tts_to_queue(accumulated_text.strip(), chunk_id, total_start, tts_speed)
            )
            tts_generation_tasks.append(tts_task)
            tts_calls.append({'chunk_id': chunk_id, 'text': accumulated_text.strip()})
        
        # Wait for all TTS generation tasks to complete (but playback continues in background)
        if tts_generation_tasks:
            tts_results = await asyncio.gather(*tts_generation_tasks, return_exceptions=True)
            # Update tts_calls with actual metrics
            for i, result in enumerate(tts_results):
                if isinstance(result, Exception):
                    print(f"   ⚠️  TTS chunk {i+1} failed: {result}")
                    tts_calls[i]['error'] = str(result)
                elif isinstance(result, dict):
                    tts_calls[i].update(result)
        
        # Wait for filler to finish if it's still playing
        if filler_task and not filler_cancelled:
            try:
                await filler_task
            except asyncio.CancelledError:
                pass
        
        # Signal end of audio queue
        await self.audio_queue.put(None)
        
        # Wait for all audio to finish playing (with timeout)
        print("   ⏳ Waiting for all audio chunks to finish playing...")
        if self.playback_task and not self.playback_task.done():
            try:
                await asyncio.wait_for(self.playback_task, timeout=60.0)
            except asyncio.TimeoutError:
                print("   ⚠️  Playback timeout after 60s")
                if self.playback_task:
                    self.playback_task.cancel()
        
        # Compute final metrics
        llm_total_time = time.time() - llm_start
        total_response = ''.join(llm_chunks)
        
        metrics['llm'] = {
            'total_time': llm_total_time,
            'first_token_time': first_token_time,
            'chunks': len(llm_chunks),
            'text': total_response
        }
        
        metrics['tts'] = {
            'calls': len(tts_calls),
            'details': tts_calls
        }
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_text})
        self.conversation_history.append({"role": "assistant", "content": total_response})
        
        # === DISPLAY FINAL COMPLETE RESPONSE ===
        print("\n" + "="*60)
        print("🤖 COMPLETE AI RESPONSE:")
        print("="*60)
        print(total_response)
        print("="*60 + "\n")
        
        # === Final Metrics ===
        total_time = time.time() - total_start
        metrics['total']['time'] = total_time
        
        # Calculate TTFA (Time To First Audio) - use actual playback time
        if self.first_audio_time:
            actual_ttfa = self.first_audio_time - total_start
            metrics['total']['ttfa'] = actual_ttfa
        elif tts_calls:
            # Fallback to estimation if first_audio_time wasn't captured
            first_tts = tts_calls[0]
            ttfa = first_tts.get('ttfb', 0)
            ttfa_from_start = (first_tts['start_time'] - total_start) + ttfa
            metrics['total']['ttfa'] = ttfa_from_start
        
        self._print_metrics(metrics)
        
        return metrics
    
    def _get_chunk_speed(self, chunk_num: int) -> float:
        """
        Calculate TTS speed for this chunk using progressive ramping
        
        Strategy:
        - First few chunks: Play slower (0.95x) to let TTS build buffer
        - Middle chunks: Gradually ramp up speed
        - Later chunks: Full speed (1.15x) once buffer is established
        
        Args:
            chunk_num: Current chunk number (1-indexed)
        
        Returns:
            Speed multiplier for this chunk
        """
        if not Config.ENABLE_SPEED_RAMPING:
            return Config.TTS_SPEED
        
        # Linear ramp from initial speed to target speed
        if chunk_num <= Config.TTS_SPEED_RAMP_CHUNKS:
            # Calculate interpolation factor (0.0 to 1.0)
            progress = (chunk_num - 1) / max(1, Config.TTS_SPEED_RAMP_CHUNKS - 1)
            
            # Linear interpolation between initial and target speed
            speed = Config.TTS_SPEED_INITIAL + (Config.TTS_SPEED - Config.TTS_SPEED_INITIAL) * progress
            return speed
        else:
            # After ramp period, use full speed
            return Config.TTS_SPEED
    
    async def _generate_tts_to_queue(
        self, 
        text: str, 
        chunk_num: int, 
        total_start_time: float,
        speed: float = None
    ) -> dict:
        """
        Generate TTS and stream audio bytes directly to playback queue (true streaming)
        
        Args:
            text: Text to synthesize
            chunk_num: Chunk number for logging
            total_start_time: Start time of entire turn
            speed: TTS playback speed (None = use default)
        
        Returns:
            dict with TTS generation metrics
        """
        if speed is None:
            speed = Config.TTS_SPEED
        
        tts_start = time.time()
        chunk_audio_queue = None
        
        try:
            # Generate TTS stream
            tts_stream = self.services.synthesize_speech_streaming_pcm_async(
                text,
                speed=speed
            )
            
            # Create a queue for this chunk's audio bytes
            chunk_audio_queue = asyncio.Queue()
            
            # Add chunk metadata to main queue (signals playback worker to start this chunk)
            await self.audio_queue.put({
                'type': 'start_chunk',
                'audio_queue': chunk_audio_queue,
                'chunk_num': chunk_num,
                'text': text,
                'start_time': tts_start
            })
            
            # Stream audio bytes to the chunk's queue as they arrive
            first_byte_time = None
            byte_count = 0
            
            async for audio_data in tts_stream:
                # TTS stream yields (bytes, metadata) tuples
                if isinstance(audio_data, tuple):
                    audio_bytes, metadata = audio_data
                    
                    # Check if done
                    if metadata.get('done'):
                        break
                else:
                    # Fallback for raw bytes
                    audio_bytes = audio_data
                
                # Skip empty bytes
                if not audio_bytes:
                    continue
                
                if first_byte_time is None:
                    first_byte_time = time.time() - tts_start
                
                # Send audio bytes to playback immediately
                await chunk_audio_queue.put(audio_bytes)
                byte_count += len(audio_bytes)
            
            # Signal end of this chunk
            await chunk_audio_queue.put(None)
            
            generation_time = time.time() - tts_start
            
            return {
                'chunk_num': chunk_num,
                'generation_time': generation_time,
                'start_time': tts_start,
                'ttfb': first_byte_time,
                'bytes': byte_count
            }
        
        except Exception as e:
            print(f"   ⚠️  TTS generation for chunk {chunk_num} failed: {e}")
            # Make sure to signal end even on error
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
    
    async def _playback_worker(self):
        """
        Worker that plays audio chunks with GAPLESS STREAMING
        - Keeps PyAudio stream open across all chunks
        - Pre-buffers next chunk while current is playing
        - Minimizes gaps between chunks
        """
        # Open a single PyAudio stream for all chunks
        stream = self.player.audio.open(
            format=self.player.format,
            channels=self.player.channels,
            rate=self.player.sample_rate,
            output=True,
            frames_per_buffer=512  # Smaller buffer for lower latency
        )
        
        try:
            while True:
                try:
                    # Get next audio chunk metadata from queue
                    audio_item = await self.audio_queue.get()
                    
                    # None signals end of audio
                    if audio_item is None:
                        self.audio_queue.task_done()
                        break
                    
                    if audio_item.get('type') == 'start_chunk':
                        chunk_num = audio_item['chunk_num']
                        chunk_audio_queue = audio_item['audio_queue']
                        
                        print(f"   ▶️  Playing audio chunk #{chunk_num} (streaming)")
                        
                        chunk_start = time.time()
                        ttfa = None
                        bytes_played = 0
                        
                        # Stream audio bytes directly to the open stream
                        try:
                            while True:
                                audio_data = await chunk_audio_queue.get()
                                if audio_data is None:
                                    # End of this chunk
                                    break
                                
                                # Extract bytes from tuple if needed (TTS returns (bytes, metadata))
                                if isinstance(audio_data, tuple):
                                    audio_bytes = audio_data[0]
                                else:
                                    audio_bytes = audio_data
                                
                                # Skip empty bytes
                                if not audio_bytes:
                                    continue
                                
                                # Record TTFA for this chunk
                                if ttfa is None:
                                    ttfa = time.time() - chunk_start
                                    
                                    # Record GLOBAL first audio time (for accurate TTFA calculation)
                                    if self.first_audio_time is None:
                                        self.first_audio_time = time.time()
                                        actual_ttfa = (self.first_audio_time - self.turn_start_time) * 1000
                                        print(f"   🔊 TTFA: {actual_ttfa:.0f}ms (Time To First Audio from start of turn)")
                                
                                # Play immediately (no buffering)
                                stream.write(audio_bytes)
                                bytes_played += len(audio_bytes)
                            
                            print(f"   ✅ Finished playing chunk #{chunk_num} ({bytes_played} bytes)")
                        
                        except Exception as e:
                            print(f"   ⚠️  Error playing chunk #{chunk_num}: {e}")
                    
                    # Mark task as done
                    self.audio_queue.task_done()
                    
                except Exception as e:
                    print(f"   ⚠️  Playback worker error: {e}")
                    self.audio_queue.task_done()
                    break
        
        finally:
            # Close the stream when all done
            try:
                stream.stop_stream()
                stream.close()
            except:
                pass
    
    async def _play_filler(self):
        """Play filler audio while waiting for LLM"""
        import random
        filler = random.choice(self.filler_phrases)
        
        print(f"   🎵 Playing filler: \"{filler}\"")
        
        try:
            # Quick TTS for filler
            tts_stream = self.services.synthesize_speech_streaming_pcm_async(
                filler,
                speed=1.0
            )
            
            await self.player.play_pcm_stream_async(tts_stream)
        
        except asyncio.CancelledError:
            print("   ⏸️  Filler playback cancelled")
            raise
    
    def _print_metrics(self, metrics: dict):
        """Print detailed metrics with timing breakdown"""
        print("\n" + "="*60)
        print("📊 PERFORMANCE METRICS")
        print("="*60)
        
        # STT
        stt = metrics['stt']
        print(f"\n🎧 STT:")
        print(f"   Latency: {stt['latency']*1000:.0f}ms")
        
        # LLM
        llm = metrics['llm']
        print(f"\n🤖 LLM:")
        print(f"   First Token: {llm['first_token_time']*1000:.0f}ms")
        print(f"   Total: {llm['total_time']*1000:.0f}ms")
        print(f"   Chunks: {llm['chunks']}")
        
        # TTS
        tts = metrics['tts']
        print(f"\n🔊 TTS:")
        print(f"   TTS Calls: {tts['calls']}")
        
        for i, call in enumerate(tts['details'], 1):
            ttfb = call.get('ttfb', 0) * 1000 if call.get('ttfb') else 0
            ttfa = call.get('ttfa', 0) * 1000 if call.get('ttfa') else 0
            total = call.get('total_time', 0) * 1000
            
            print(f"   Call {i}:")
            print(f"     TTFB: {ttfb:.0f}ms | TTFA: {ttfa:.0f}ms | Total: {total:.0f}ms")
            print(f"     Text: \"{call.get('text', '')[:40]}...\"")
        
        # Total with breakdown
        total = metrics['total']
        ttfa_total = total.get('ttfa', 0) * 1000
        total_time = total['time'] * 1000
        
        stt_time = stt['latency'] * 1000
        llm_first_token = llm['first_token_time'] * 1000
        
        print(f"\n⏱️  TOTAL:")
        print(f"   TTFA (Time To First Audio): {ttfa_total:.0f}ms")
        print(f"   End-to-End: {total_time:.0f}ms")
        
        # Breakdown
        print(f"\n📊 TTFA Breakdown:")
        print(f"   1. STT (transcription): {stt_time:.0f}ms")
        print(f"   2. LLM (first token): {llm_first_token:.0f}ms")
        
        # Calculate TTS generation + playback time
        tts_and_playback = ttfa_total - stt_time - llm_first_token
        print(f"   3. TTS generation + playback: {tts_and_playback:.0f}ms")
        print(f"   ─────────────────────────────")
        print(f"   Total TTFA: {ttfa_total:.0f}ms")
        
        print("\n" + "="*60)
        
        # Assessment
        if ttfa_total < 1500:
            print("🚀 EXCELLENT! TTFA < 1.5s")
        elif ttfa_total < 2000:
            print("✅ GOOD! TTFA < 2s")
        elif ttfa_total < 2500:
            print("⚠️  ACCEPTABLE. TTFA < 2.5s")
        else:
            print("❌ SLOW. TTFA > 2.5s - Check optimizations")
        
        print("="*60)
    
    async def close(self):
        """Cleanup"""
        await self.services.close()

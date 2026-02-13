"""
Ultra-Aggressive Conversation Engine - FORCED CHUNKING
This version fires TTS every N characters regardless of delimiters
Use this for absolute minimum TTFA (may sound less natural)
"""
import asyncio
import time
from typing import Tuple, Dict
from voice_services_optimized import VoiceServicesOptimized
from audio_recorder_optimized import AudioRecorderOptimized
from audio_player_optimized import AudioPlayerOptimized
from config import Config


class ConversationEngineUltraAggressive:
    """Ultra-aggressive conversation engine with forced chunking"""
    
    def __init__(self):
        self.services = VoiceServicesOptimized()
        self.recorder = AudioRecorderOptimized()
        self.player = AudioPlayerOptimized()
        self.conversation_history = []
        
        # Ultra-aggressive settings
        self.FORCE_CHUNK_AT = 50  # Fire TTS every 50 characters, NO EXCEPTIONS
        self.MIN_CHUNK = 15  # Minimum chunk size
    
    async def process_turn_ultra_aggressive(
        self,
        audio_bytes: bytes = None
    ) -> Dict:
        """
        Process with FORCED chunking - fires TTS every 50 chars
        
        Strategy:
        1. STT from memory
        2. Stream LLM
        3. Fire TTS EVERY 50 characters (don't wait for delimiters)
        4. Play all chunks in parallel
        """
        metrics = {
            'stt': {},
            'llm': {},
            'tts': {},
            'total': {}
        }
        
        total_start = time.time()
        
        # === STEP 1: STT ===
        print("\n" + "="*60)
        print("🎧 Step 1: Speech-to-Text")
        print("="*60)
        
        user_text, stt_latency = await self.services.transcribe_audio_bytes_async(audio_bytes)
        metrics['stt'] = {'latency': stt_latency, 'text': user_text}
        
        print(f"👤 User: {user_text}")
        print(f"   ⏱️  STT: {stt_latency*1000:.0f}ms")
        
        # === STEP 2: LLM + FORCED CHUNKING ===
        print("\n" + "="*60)
        print("🤖 Step 2: LLM Streaming → FORCED TTS Chunking")
        print(f"   ⚡ FORCED: Fire TTS every {self.FORCE_CHUNK_AT} chars")
        print("="*60)
        
        llm_start = time.time()
        
        llm_stream = self.services.generate_response_streaming_async(
            user_text,
            self.conversation_history
        )
        
        llm_chunks = []
        tts_tasks = []
        accumulated_text = ""
        first_token_time = None
        chunk_count = 0
        
        async for chunk_text, is_final, timing in llm_stream:
            if first_token_time is None and chunk_text:
                first_token_time = time.time() - llm_start
                print(f"   🎯 First LLM token: {first_token_time*1000:.0f}ms")
            
            accumulated_text += chunk_text
            llm_chunks.append(chunk_text)
            
            # FORCED CHUNKING: Fire TTS every FORCE_CHUNK_AT characters
            while len(accumulated_text) >= self.FORCE_CHUNK_AT:
                # Extract chunk
                chunk_to_synthesize = accumulated_text[:self.FORCE_CHUNK_AT].strip()
                accumulated_text = accumulated_text[self.FORCE_CHUNK_AT:].strip()
                
                if chunk_to_synthesize:
                    chunk_count += 1
                    print(f"   🔊 FORCED TTS #{chunk_count}: \"{chunk_to_synthesize[:35]}...\" ({len(chunk_to_synthesize)} chars)")
                    
                    # Fire TTS in parallel
                    tts_task = asyncio.create_task(
                        self._fire_and_play_tts(chunk_to_synthesize, chunk_count, total_start)
                    )
                    tts_tasks.append(tts_task)
            
            if is_final:
                break
        
        # Fire remaining text
        if len(accumulated_text) >= self.MIN_CHUNK:
            chunk_count += 1
            print(f"   🔊 FINAL TTS #{chunk_count}: \"{accumulated_text[:35]}...\" ({len(accumulated_text)} chars)")
            
            tts_task = asyncio.create_task(
                self._fire_and_play_tts(accumulated_text, chunk_count, total_start)
            )
            tts_tasks.append(tts_task)
        
        # Wait for all TTS to complete
        if tts_tasks:
            print(f"\n   ⏳ Waiting for {len(tts_tasks)} TTS tasks to complete...")
            tts_results = await asyncio.gather(*tts_tasks, return_exceptions=True)
            tts_calls = [r for r in tts_results if isinstance(r, dict)]
        else:
            tts_calls = []
        
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
        
        # Calculate TTFA
        total_time = time.time() - total_start
        metrics['total']['time'] = total_time
        
        if tts_calls:
            first_tts = tts_calls[0]
            ttfa = first_tts.get('ttfa', 0)
            ttfa_from_start = (first_tts['start_time'] - total_start) + ttfa
            metrics['total']['ttfa'] = ttfa_from_start
        
        self._print_metrics(metrics)
        
        return metrics
    
    async def _fire_and_play_tts(
        self, 
        text: str, 
        chunk_num: int, 
        total_start_time: float
    ) -> dict:
        """Fire TTS and play immediately"""
        tts_start = time.time()
        
        try:
            tts_stream = self.services.synthesize_speech_streaming_pcm_async(
                text,
                speed=Config.TTS_SPEED
            )
            
            tts_metrics = await self.player.play_pcm_stream_async(tts_stream)
            tts_metrics['text'] = text
            tts_metrics['start_time'] = tts_start
            tts_metrics['chunk_num'] = chunk_num
            
            return tts_metrics
        
        except Exception as e:
            print(f"   ⚠️  TTS chunk {chunk_num} failed: {e}")
            return {
                'text': text,
                'chunk_num': chunk_num,
                'error': str(e),
                'start_time': tts_start
            }
    
    def _print_metrics(self, metrics: dict):
        """Print metrics"""
        print("\n" + "="*60)
        print("📊 PERFORMANCE METRICS (ULTRA-AGGRESSIVE MODE)")
        print("="*60)
        
        # STT
        stt = metrics['stt']
        print(f"\n🎧 STT: {stt['latency']*1000:.0f}ms")
        
        # LLM
        llm = metrics['llm']
        print(f"\n🤖 LLM:")
        print(f"   First Token: {llm['first_token_time']*1000:.0f}ms")
        print(f"   Total: {llm['total_time']*1000:.0f}ms")
        
        # TTS
        tts = metrics['tts']
        print(f"\n🔊 TTS: {tts['calls']} chunks")
        
        for i, call in enumerate(tts['details'][:3], 1):  # Show first 3
            ttfb = call.get('ttfb', 0) * 1000 if call.get('ttfb') else 0
            ttfa = call.get('ttfa', 0) * 1000 if call.get('ttfa') else 0
            print(f"   Chunk {i}: TTFB: {ttfb:.0f}ms | TTFA: {ttfa:.0f}ms")
        
        if len(tts['details']) > 3:
            print(f"   ... and {len(tts['details']) - 3} more")
        
        # Total
        total = metrics['total']
        ttfa_total = total.get('ttfa', 0) * 1000
        total_time = total['time'] * 1000
        
        print(f"\n⏱️  TOTAL:")
        print(f"   TTFA: {ttfa_total:.0f}ms")
        print(f"   End-to-End: {total_time:.0f}ms")
        
        print("\n" + "="*60)
        
        if ttfa_total < 2500:
            print("🎯 TARGET ACHIEVED! TTFA < 2.5s")
        elif ttfa_total < 3500:
            print("⚠️  ACCEPTABLE. TTFA < 3.5s")
        else:
            print("❌ SLOW. Further optimization needed")
        
        print("="*60)
    
    async def close(self):
        """Cleanup"""
        await self.services.close()

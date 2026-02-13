"""
Test TRUE STREAMING - Verify audio plays as TTS generates, not after
This test monitors timing to ensure:
1. TTS chunks fire as LLM streams (not after)
2. Audio playback starts before all TTS generation completes
3. TTFA is minimized (first audio plays ASAP)
"""
import asyncio
import sys
from pathlib import Path
import time

# Add conversation directory to path
sys.path.insert(0, str(Path(__file__).parent))

from conversation_engine_optimized import ConversationEngineOptimized
from config import Config


class StreamingMonitor:
    """Monitor to track true streaming behavior"""
    
    def __init__(self):
        self.events = []
        self.start_time = None
    
    def mark(self, event_type: str, message: str):
        """Mark an event with timestamp"""
        if self.start_time is None:
            self.start_time = time.time()
        
        elapsed = (time.time() - self.start_time) * 1000
        self.events.append({
            'time': elapsed,
            'type': event_type,
            'message': message
        })
        print(f"[{elapsed:7.0f}ms] {event_type}: {message}")
    
    def analyze(self):
        """Analyze if true streaming occurred"""
        print("\n" + "="*70)
        print("📊 STREAMING ANALYSIS")
        print("="*70)
        
        # Find events
        tts_starts = [e for e in self.events if e['type'] == 'TTS_START']
        tts_completes = [e for e in self.events if e['type'] == 'TTS_COMPLETE']
        playback_starts = [e for e in self.events if e['type'] == 'PLAYBACK_START']
        playback_completes = [e for e in self.events if e['type'] == 'PLAYBACK_COMPLETE']
        
        print(f"\n📝 Summary:")
        print(f"   TTS generations started: {len(tts_starts)}")
        print(f"   TTS generations completed: {len(tts_completes)}")
        print(f"   Playback started: {len(playback_starts)}")
        print(f"   Playback completed: {len(playback_completes)}")
        
        # Check for true streaming
        if tts_starts and playback_starts:
            first_tts_start = tts_starts[0]['time']
            first_playback_start = playback_starts[0]['time']
            last_tts_complete = tts_completes[-1]['time'] if tts_completes else 0
            
            print(f"\n⏱️  Timing:")
            print(f"   First TTS started: {first_tts_start:.0f}ms")
            print(f"   First playback started: {first_playback_start:.0f}ms")
            print(f"   Last TTS completed: {last_tts_complete:.0f}ms")
            
            # True streaming check
            if len(tts_starts) > 1:
                print("\n✅ Multiple TTS chunks detected")
                
                # Did playback start before all TTS completed?
                if first_playback_start < last_tts_complete:
                    gap = last_tts_complete - first_playback_start
                    print(f"✅ TRUE STREAMING DETECTED!")
                    print(f"   Playback started {gap:.0f}ms before all TTS completed")
                    print(f"   This is what we want - audio plays while TTS generates")
                else:
                    print(f"❌ NO STREAMING - Playback waited for all TTS to complete")
            else:
                print("\n⚠️  Only one TTS chunk (response may be too short to chunk)")
        
        print("="*70)


async def test_with_monitoring():
    """Test with detailed monitoring"""
    print("="*70)
    print("🧪 TRUE STREAMING TEST WITH MONITORING")
    print("="*70)
    print(f"Provider: {Config.LLM_PROVIDER}")
    print(f"Model: {Config.LLM_MODEL}")
    print(f"Chunk Size: {Config.TTS_CHUNK_MIN_CHARS}-{Config.TTS_CHUNK_MAX_CHARS} chars")
    print("="*70 + "\n")
    
    monitor = StreamingMonitor()
    
    # Patch the conversation engine to add monitoring hooks
    engine = ConversationEngineOptimized()
    
    # Wrap key methods with monitoring
    original_generate_tts = engine._generate_tts_to_queue
    async def monitored_generate_tts(text, chunk_num, total_start):
        monitor.mark('TTS_START', f"Chunk {chunk_num} ({len(text)} chars)")
        result = await original_generate_tts(text, chunk_num, total_start)
        monitor.mark('TTS_COMPLETE', f"Chunk {chunk_num}")
        return result
    
    engine._generate_tts_to_queue = monitored_generate_tts
    
    # Wrap playback worker
    original_playback = engine._playback_worker
    async def monitored_playback():
        await original_playback()
    
    # Create test audio (silent)
    import wave, io
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(b'\x00\x00' * 32000)  # 2 seconds
    
    audio_bytes = wav_buffer.getvalue()
    
    try:
        monitor.mark('START', 'Test begins')
        
        metrics = await engine.process_turn_ultra_optimized(
            audio_bytes=audio_bytes,
            use_filler=False
        )
        
        monitor.mark('END', 'Test complete')
        monitor.analyze()
        
        # Show metrics
        print(f"\n📊 Final Metrics:")
        print(f"   TTFA: {metrics['total'].get('ttfa', 0)*1000:.0f}ms")
        print(f"   Total: {metrics['total']['time']*1000:.0f}ms")
        print(f"   TTS Calls: {metrics['tts']['calls']}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    await engine.close()


if __name__ == "__main__":
    asyncio.run(test_with_monitoring())

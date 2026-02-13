"""
Quick test to verify multi-chunk TTS streaming fix
This will show how many TTS calls are made for a typical response
"""
import asyncio
import sys
from pathlib import Path

# Add conversation directory to path
sys.path.insert(0, str(Path(__file__).parent))

from conversation_engine_optimized import ConversationEngineOptimized
from config import Config


async def test_streaming():
    """Test streaming with a sample question"""
    print("="*70)
    print("🧪 TESTING MULTI-CHUNK TTS STREAMING FIX")
    print("="*70)
    print(f"Provider: {Config.LLM_PROVIDER}")
    print(f"Model: {Config.LLM_MODEL}")
    print(f"Min Chunk: {Config.TTS_CHUNK_MIN_CHARS} chars")
    print(f"Max Chunk: {Config.TTS_CHUNK_MAX_CHARS} chars")
    print("="*70)
    
    # Create mock audio data (will be replaced with actual recording in full app)
    # For this test, we'll simulate with a text input
    print("\n⚠️  Note: This is a simplified test using text input")
    print("    In production, audio would come from the recorder\n")
    
    # You can modify this to test with actual audio
    test_question = "Merhaba, bugün nasılsın?"
    print(f"Test Question: {test_question}\n")
    
    # Create a simple WAV header for testing (silent audio)
    import wave
    import io
    
    # Create 2 seconds of silence at 16kHz mono
    sample_rate = 16000
    duration = 2
    num_samples = sample_rate * duration
    
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(b'\x00\x00' * num_samples)
    
    audio_bytes = wav_buffer.getvalue()
    
    print("🎤 Note: Using silent audio (STT will likely return empty or error)")
    print("    Focus on the LLM→TTS streaming behavior\n")
    
    # Run conversation engine
    engine = ConversationEngineOptimized()
    
    try:
        metrics = await engine.process_turn_ultra_optimized(
            audio_bytes=audio_bytes,
            use_filler=False  # Disable filler for cleaner test
        )
        
        print("\n" + "="*70)
        print("📊 TEST RESULTS")
        print("="*70)
        print(f"✅ LLM Chunks received: {metrics['llm']['chunks']}")
        print(f"✅ TTS Calls made: {metrics['tts']['calls']}")
        print(f"✅ TTFA (Time to First Audio): {metrics['total'].get('ttfa', 0)*1000:.0f}ms")
        print(f"✅ Total Time: {metrics['total']['time']*1000:.0f}ms")
        
        if metrics['tts']['calls'] > 1:
            print("\n🎉 SUCCESS! Multiple TTS chunks are being fired!")
            print("   This means streaming is working correctly.")
        else:
            print("\n⚠️  Only 1 TTS call detected.")
            print("   This might be expected if the response was very short,")
            print("   or there might still be an issue with chunking logic.")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_streaming())

"""
Test True Streaming Implementation
This script verifies that audio chunks are received and played progressively
"""
import asyncio
import time
from voice_services import VoiceServices
from audio_player import AudioPlayer
from config import Config


async def test_streaming():
    """Test true streaming TTS"""
    print("="*60)
    print("🧪 Testing TRUE Streaming TTS")
    print("="*60)
    
    services = VoiceServices()
    player = AudioPlayer()
    
    test_text = "Merhaba! Ben bir yapay zeka asistanıyım. Size nasıl yardımcı olabilirim?"
    
    print(f"\n📝 Text: {test_text}")
    print(f"🔧 Streaming: {Config.ENABLE_STREAMING_TTS}")
    print(f"🌐 Endpoint: {Config.TTS_STREAM_URL}")
    print()
    
    # Test streaming
    start_time = time.time()
    first_chunk_time = None
    chunk_count = 0
    
    print("⏳ Requesting audio stream...")
    
    try:
        # Get streaming iterator
        audio_stream = services.synthesize_speech_streaming_async(test_text)
        
        # Collect chunks and measure timing
        chunks = []
        async for chunk in audio_stream:
            chunk_count += 1
            chunks.append(chunk)
            
            if first_chunk_time is None:
                first_chunk_time = time.time()
                ttfb = first_chunk_time - start_time
                print(f"✅ First chunk received! TTFB: {ttfb:.3f}s")
            
            if chunk_count <= 5 or chunk_count % 10 == 0:
                print(f"   Chunk {chunk_count}: {len(chunk)} bytes")
        
        total_receive_time = time.time() - start_time
        
        print()
        print("📊 Streaming Statistics:")
        print(f"   • Total chunks: {chunk_count}")
        print(f"   • TTFB (Time-To-First-Byte): {ttfb:.3f}s")
        print(f"   • Total receive time: {total_receive_time:.3f}s")
        print(f"   • Total audio size: {sum(len(c) for c in chunks)} bytes")
        print()
        
        # Now play the complete audio
        print("🔊 Playing complete audio...")
        play_start = time.time()
        
        # Convert chunks to bytes and play
        audio_data = b''.join(chunks)
        player.play_bytes(audio_data)
        
        play_time = time.time() - play_start
        total_time = time.time() - start_time
        
        print()
        print("✅ Streaming Test Complete!")
        print(f"   • Play time: {play_time:.3f}s")
        print(f"   • Total time: {total_time:.3f}s")
        print()
        
        # Assessment
        if ttfb < 0.5:
            print("🚀 EXCELLENT! TTFB < 500ms")
        elif ttfb < 1.0:
            print("✅ GOOD! TTFB < 1s")
        else:
            print("⚠️  High TTFB. Check network or API.")
        
        print()
        print("💡 With true streaming, the audio would start playing")
        print("   as soon as the first chunk arrives, reducing perceived latency!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await services.close()


async def test_full_streaming_pipeline():
    """Test the complete streaming pipeline with immediate playback"""
    print("\n" + "="*60)
    print("🧪 Testing Full Streaming Pipeline (Play As Received)")
    print("="*60)
    
    services = VoiceServices()
    player = AudioPlayer()
    
    test_text = "Bu bir gerçek zamanlı akış testi. Ses parçaları geldikçe çalınacak."
    
    print(f"\n📝 Text: {test_text}")
    print("⏳ Starting streaming with immediate playback...")
    print()
    
    try:
        start_time = time.time()
        
        # Get streaming iterator and play immediately
        audio_stream = services.synthesize_speech_streaming_async(test_text)
        
        # This will play as chunks arrive
        await player.play_streaming_async(audio_stream)
        
        total_time = time.time() - start_time
        
        print()
        print(f"✅ Streaming pipeline complete! Total time: {total_time:.3f}s")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await services.close()


if __name__ == "__main__":
    print("\n🎙️  TRUE STREAMING TEST\n")
    print("This test verifies that:")
    print("  1. Audio chunks arrive progressively from the API")
    print("  2. TTFB (Time-To-First-Byte) is measured")
    print("  3. Audio can be played as chunks arrive")
    print()
    
    # Run tests
    asyncio.run(test_streaming())
    asyncio.run(test_full_streaming_pipeline())

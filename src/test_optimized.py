"""
Ultra-Optimized System Test
Tests all optimizations and measures TTFA
"""
import asyncio
import time
from pathlib import Path
from voice_services_optimized import VoiceServicesOptimized
from audio_recorder_optimized import AudioRecorderOptimized
from audio_player_optimized import AudioPlayerOptimized
from conversation_engine_optimized import ConversationEngineOptimized


async def test_in_memory_stt():
    """Test in-memory STT (no disk I/O)"""
    print("\n" + "="*60)
    print("🧪 TEST 1: In-Memory STT")
    print("="*60)
    
    recorder = AudioRecorderOptimized()
    services = VoiceServicesOptimized()
    
    print("Recording 3 seconds...")
    audio_bytes = recorder.record_to_memory_manual(duration=3)
    
    print(f"✅ Recorded {len(audio_bytes)} bytes in memory")
    print("Transcribing...")
    
    text, latency = await services.transcribe_audio_bytes_async(audio_bytes)
    
    print(f"📝 Text: {text}")
    print(f"⏱️  Latency: {latency*1000:.0f}ms")
    
    await services.close()
    
    if latency < 1.0:
        print("🚀 EXCELLENT! < 1s")
    elif latency < 1.5:
        print("✅ GOOD! < 1.5s")
    else:
        print("⚠️  Can be optimized")


async def test_llm_streaming():
    """Test LLM streaming"""
    print("\n" + "="*60)
    print("🧪 TEST 2: LLM Streaming")
    print("="*60)
    
    services = VoiceServicesOptimized()
    
    prompt = "Merhaba, sen kimsin?"
    print(f"📝 Prompt: {prompt}")
    
    start = time.time()
    first_token_time = None
    chunks = []
    
    print("\nStreaming LLM response:")
    
    async for chunk, is_final, timing in services.generate_response_streaming_async(prompt):
        if first_token_time is None and chunk:
            first_token_time = time.time() - start
            print(f"   🎯 First token: {first_token_time*1000:.0f}ms")
        
        chunks.append(chunk)
        print(f"   📦 Chunk: \"{chunk}\"")
        
        if is_final:
            break
    
    total_time = time.time() - start
    full_text = ''.join(chunks)
    
    print(f"\n✅ Complete: {full_text}")
    print(f"⏱️  Total: {total_time*1000:.0f}ms")
    print(f"⏱️  First Token: {first_token_time*1000:.0f}ms")
    print(f"📦 Chunks: {len(chunks)}")
    
    await services.close()
    
    if first_token_time < 0.5:
        print("🚀 EXCELLENT first token time!")
    elif first_token_time < 1.0:
        print("✅ GOOD first token time")


async def test_tts_pcm_streaming():
    """Test TTS PCM streaming"""
    print("\n" + "="*60)
    print("🧪 TEST 3: TTS PCM Streaming")
    print("="*60)
    
    services = VoiceServicesOptimized()
    player = AudioPlayerOptimized()
    
    text = "Merhaba! Bu bir test mesajıdır."
    print(f"📝 Text: {text}")
    print("🔊 Streaming TTS...")
    
    start = time.time()
    
    tts_stream = services.synthesize_speech_streaming_pcm_async(text, speed=1.1)
    metrics = await player.play_pcm_stream_async(tts_stream)
    
    total = time.time() - start
    
    print(f"\n✅ TTS Complete")
    print(f"⏱️  TTFB: {metrics['ttfb']*1000:.0f}ms")
    print(f"⏱️  TTFA: {metrics['ttfa']*1000:.0f}ms")
    print(f"⏱️  Total: {total*1000:.0f}ms")
    print(f"📦 Chunks: {metrics['chunks_played']}")
    
    await services.close()
    
    if metrics['ttfa'] < 0.5:
        print("🚀 EXCELLENT TTFA!")
    elif metrics['ttfa'] < 1.0:
        print("✅ GOOD TTFA")


async def test_full_pipeline():
    """Test full ultra-optimized pipeline"""
    print("\n" + "="*60)
    print("🧪 TEST 4: Full Ultra-Optimized Pipeline")
    print("="*60)
    
    engine = ConversationEngineOptimized()
    recorder = AudioRecorderOptimized()
    
    print("Recording 3 seconds...")
    audio_bytes = recorder.record_to_memory_manual(duration=3)
    
    print(f"✅ Recorded {len(audio_bytes)} bytes")
    print("\nProcessing with full pipeline...\n")
    
    metrics = await engine.process_turn_ultra_optimized(
        audio_bytes=audio_bytes,
        use_filler=True
    )
    
    await engine.close()


async def test_from_wav_file():
    """Test from existing WAV file"""
    print("\n" + "="*60)
    print("🧪 TEST 5: From WAV File")
    print("="*60)
    
    # Find a test WAV file
    test_files = list(Path("outputs").glob("user_audio_*.wav"))
    
    if not test_files:
        print("⚠️  No test WAV files found in outputs/")
        print("   Record some audio first using main_optimized.py")
        return
    
    test_file = test_files[0]
    print(f"📁 Using: {test_file}")
    
    audio_bytes = test_file.read_bytes()
    
    engine = ConversationEngineOptimized()
    
    metrics = await engine.process_turn_ultra_optimized(
        audio_bytes=audio_bytes,
        use_filler=True
    )
    
    await engine.close()


async def main():
    print("\n" + "🚀"*30)
    print("ULTRA-OPTIMIZED SYSTEM TESTS")
    print("🚀"*30)
    
    tests = [
        ("In-Memory STT", test_in_memory_stt),
        ("LLM Streaming", test_llm_streaming),
        ("TTS PCM Streaming", test_tts_pcm_streaming),
        ("Full Pipeline", test_full_pipeline),
        ("From WAV File", test_from_wav_file),
    ]
    
    for i, (name, test_func) in enumerate(tests, 1):
        try:
            await test_func()
        except KeyboardInterrupt:
            print("\n\n⏸️  Tests interrupted")
            break
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        
        if i < len(tests):
            print("\n" + "─"*60)
            input("Press Enter for next test...")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())

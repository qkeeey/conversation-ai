"""
Quick Test Script - Verify Critical Optimizations
Tests:
1. VAD ring buffer (doesn't cut off speech)
2. Multiple TTS calls (sentence chunking)
3. Shorter responses (<80 tokens)
4. Improved TTFA (<2500ms target)
"""
import asyncio
from pathlib import Path
from conversation_engine_optimized import ConversationEngineOptimized
from config import Config


async def test_file_processing():
    """Test with recording01.wav to verify improvements"""
    print("="*70)
    print("🧪 TESTING CRITICAL OPTIMIZATIONS")
    print("="*70)
    
    # Check config
    print("\n📋 Configuration Check:")
    print(f"  LLM Model: {Config.LLM_MODEL}")
    print(f"  Max Tokens: {Config.LLM_MAX_TOKENS}")
    print(f"  Temperature: {Config.LLM_TEMPERATURE}")
    print(f"  TTS Speed: {Config.TTS_SPEED}")
    print(f"  TTS Chunk Min: {Config.TTS_CHUNK_MIN_CHARS} chars")
    print(f"  TTS Chunk Max: {Config.TTS_CHUNK_MAX_CHARS} chars")
    print(f"  VAD Silence: {Config.SILENCE_DURATION}s")
    print(f"  VAD Min Speech: {Config.MIN_SPEECH_DURATION}s")
    print(f"  VAD Ring Buffer: {Config.RING_BUFFER_SIZE} frames (~{Config.RING_BUFFER_SIZE*30}ms)")
    
    # Load test audio
    audio_file = Path("data/recording01.wav")
    if not audio_file.exists():
        print(f"\n❌ Test file not found: {audio_file}")
        print("   Please provide a test audio file.")
        return
    
    print(f"\n📁 Test Audio: {audio_file}")
    audio_bytes = audio_file.read_bytes()
    
    # Process
    print("\n" + "="*70)
    print("🚀 Processing with optimizations...")
    print("="*70)
    
    engine = ConversationEngineOptimized()
    
    try:
        metrics = await engine.process_turn_ultra_optimized(
            audio_bytes=audio_bytes,
            use_filler=True
        )
        
        # Analyze results
        print("\n" + "="*70)
        print("📊 OPTIMIZATION VERIFICATION")
        print("="*70)
        
        # Check 1: TTS Calls
        tts_calls = metrics['tts']['calls']
        print(f"\n✓ TTS Calls: {tts_calls}")
        if tts_calls > 1:
            print("  ✅ PASS: Multiple TTS calls (sentence chunking working)")
        else:
            print("  ⚠️  WARN: Only 1 TTS call (chunking may need tuning)")
        
        # Check 2: TTFA
        ttfa_ms = metrics['total'].get('ttfa', 0) * 1000
        print(f"\n✓ TTFA: {ttfa_ms:.0f}ms")
        if ttfa_ms < 2500:
            print("  ✅ PASS: TTFA < 2500ms (target achieved!)")
        elif ttfa_ms < 3500:
            print("  ⚠️  ACCEPTABLE: TTFA < 3500ms (close to target)")
        else:
            print("  ❌ FAIL: TTFA > 3500ms (needs optimization)")
        
        # Check 3: Response Length
        response_text = metrics['llm']['text']
        response_words = len(response_text.split())
        response_chars = len(response_text)
        print(f"\n✓ Response: {response_words} words, {response_chars} chars")
        if response_words <= 80:
            print("  ✅ PASS: Response concise (<80 words)")
        elif response_words <= 120:
            print("  ⚠️  ACCEPTABLE: Response reasonable (<120 words)")
        else:
            print("  ❌ FAIL: Response too long (>120 words)")
        
        # Check 4: LLM First Token
        first_token_ms = metrics['llm']['first_token_time'] * 1000
        print(f"\n✓ LLM First Token: {first_token_ms:.0f}ms")
        if first_token_ms < 1000:
            print("  ✅ PASS: Fast LLM response (<1000ms)")
        elif first_token_ms < 1500:
            print("  ⚠️  ACCEPTABLE: LLM response reasonable (<1500ms)")
        else:
            print("  ❌ SLOW: LLM response slow (>1500ms)")
        
        # Check 5: TTS TTFB (first call)
        if tts_calls > 0:
            first_tts = metrics['tts']['details'][0]
            tts_ttfb_ms = first_tts.get('ttfb', 0) * 1000
            print(f"\n✓ TTS TTFB (first chunk): {tts_ttfb_ms:.0f}ms")
            if tts_ttfb_ms < 1000:
                print("  ✅ PASS: Fast TTS response (<1000ms)")
            elif tts_ttfb_ms < 1500:
                print("  ⚠️  ACCEPTABLE: TTS response reasonable (<1500ms)")
            else:
                print("  ❌ SLOW: TTS response slow (>1500ms)")
        
        # Summary
        print("\n" + "="*70)
        print("📈 SUMMARY")
        print("="*70)
        
        passes = 0
        if tts_calls > 1:
            passes += 1
        if ttfa_ms < 3500:
            passes += 1
        if response_words <= 120:
            passes += 1
        if first_token_ms < 1500:
            passes += 1
        if tts_calls > 0 and first_tts.get('ttfb', 0) * 1000 < 1500:
            passes += 1
        
        print(f"\nPassed: {passes}/5 checks")
        
        if passes >= 4:
            print("✅ EXCELLENT: Optimizations working well!")
        elif passes >= 3:
            print("⚠️  GOOD: Most optimizations working, some tuning needed")
        else:
            print("❌ NEEDS WORK: Multiple optimizations need debugging")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if tts_calls == 1:
            print("  - Debug TTS chunking logic (check sentence delimiters)")
        if ttfa_ms > 3000:
            print("  - Consider faster LLM model or lower max_tokens")
        if response_words > 100:
            print("  - Strengthen system prompt for brevity")
        if first_token_ms > 1200:
            print("  - Try different LLM model (e.g., Claude Haiku)")
        
        print("\n" + "="*70)
    
    finally:
        await engine.close()


async def test_vad_parameters():
    """Display VAD configuration for manual testing"""
    print("\n" + "="*70)
    print("🎤 VAD CONFIGURATION TEST")
    print("="*70)
    
    print("\nCurrent VAD Settings:")
    print(f"  Silence Duration: {Config.SILENCE_DURATION}s")
    print(f"  Min Speech Duration: {Config.MIN_SPEECH_DURATION}s")
    print(f"  Ring Buffer: {Config.RING_BUFFER_SIZE} frames (~{Config.RING_BUFFER_SIZE*30}ms pre-roll)")
    print(f"  VAD Mode: {Config.VAD_MODE} (0=quality, 3=aggressive)")
    
    print("\nExpected Behavior:")
    print("  ✓ Captures ~300ms of audio BEFORE speech detected")
    print("  ✓ Requires at least 0.3s of speech (prevents false triggers)")
    print("  ✓ Ends after 0.6s of silence (responsive but not too aggressive)")
    print("  ✓ Does NOT cut off after 1-2 words")
    
    print("\nTo test manually:")
    print("  python main_optimized.py --vad")
    print("  Then speak a full sentence - it should NOT cut you off!")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 CRITICAL OPTIMIZATIONS TEST SUITE")
    print("="*70)
    
    # Test 1: VAD Config
    asyncio.run(test_vad_parameters())
    
    # Test 2: File Processing
    print("\n")
    asyncio.run(test_file_processing())
    
    print("\n✅ Testing complete!")

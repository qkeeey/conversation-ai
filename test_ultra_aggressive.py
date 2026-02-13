"""
Test Ultra-Aggressive Forced Chunking
This will fire TTS every 50 characters regardless of delimiters
"""
import asyncio
from pathlib import Path
from conversation_engine_ultra_aggressive import ConversationEngineUltraAggressive


async def test_forced_chunking():
    print("="*70)
    print("🚀 TESTING ULTRA-AGGRESSIVE FORCED CHUNKING")
    print("="*70)
    print("\nStrategy: Fire TTS every 50 characters (no delimiter wait)")
    print("Expected: 3-5 TTS calls, much lower TTFA")
    print("="*70)
    
    # Load test audio
    audio_file = Path("data/recording01.wav")
    if not audio_file.exists():
        print(f"\n❌ Test file not found: {audio_file}")
        return
    
    audio_bytes = audio_file.read_bytes()
    
    # Process with ultra-aggressive engine
    engine = ConversationEngineUltraAggressive()
    
    try:
        metrics = await engine.process_turn_ultra_aggressive(audio_bytes=audio_bytes)
        
        # Analysis
        print("\n" + "="*70)
        print("📊 ANALYSIS")
        print("="*70)
        
        tts_calls = metrics['tts']['calls']
        ttfa = metrics['total'].get('ttfa', 0) * 1000
        
        print(f"\n✓ TTS Calls: {tts_calls}")
        if tts_calls >= 3:
            print("  ✅ EXCELLENT: Multiple TTS calls (forced chunking working!)")
        elif tts_calls >= 2:
            print("  ✅ GOOD: 2 TTS calls")
        else:
            print("  ❌ FAIL: Only 1 TTS call (forced chunking failed)")
        
        print(f"\n✓ TTFA: {ttfa:.0f}ms")
        if ttfa < 2500:
            print("  🎯 TARGET ACHIEVED! TTFA < 2500ms")
        elif ttfa < 3500:
            print("  ⚠️  ACCEPTABLE: TTFA < 3500ms")
        else:
            print("  ❌ SLOW: TTFA > 3500ms")
        
        # Comparison
        print("\n" + "="*70)
        print("📈 IMPROVEMENT vs PREVIOUS")
        print("="*70)
        
        previous_ttfa = 5038
        improvement = ((previous_ttfa - ttfa) / previous_ttfa) * 100
        
        print(f"\nPrevious TTFA: {previous_ttfa}ms")
        print(f"Current TTFA:  {ttfa:.0f}ms")
        print(f"Improvement:   {improvement:.1f}%")
        
        if improvement > 30:
            print("\n🎉 MAJOR IMPROVEMENT!")
        elif improvement > 0:
            print("\n✅ IMPROVEMENT ACHIEVED")
        else:
            print("\n❌ NO IMPROVEMENT")
        
        print("\n" + "="*70)
    
    finally:
        await engine.close()


if __name__ == "__main__":
    asyncio.run(test_forced_chunking())

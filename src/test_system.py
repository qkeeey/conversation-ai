"""
Quick Test Script for Conversational AI
Tests all components without requiring microphone input
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from voice_services import VoiceServices
import asyncio
import time


def test_configuration():
    """Test 1: Configuration"""
    print("\n" + "="*60)
    print("TEST 1: Configuration")
    print("="*60)
    
    try:
        Config.validate()
        print("✅ Configuration valid")
        print(f"   FAL_KEY: {Config.FAL_KEY[:10]}...{Config.FAL_KEY[-5:]}")
        print(f"   OPENROUTER_KEY: {Config.OPENROUTER_KEY[:15]}...{Config.OPENROUTER_KEY[-5:]}")
        print(f"   TTS URL: {Config.TTS_SPEECH_URL}")
        print(f"   STT URL: {Config.STT_TRANSCRIBE_URL}")
        print(f"   LLM URL: {Config.LLM_URL}")
        return True
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        return False


def test_tts():
    """Test 2: Text-to-Speech"""
    print("\n" + "="*60)
    print("TEST 2: Text-to-Speech")
    print("="*60)
    
    try:
        services = VoiceServices()
        test_text = "Merhaba, bu bir test mesajıdır."
        
        print(f"Testing TTS with: '{test_text}'")
        start = time.time()
        
        audio_file = services.synthesize_speech(test_text, "test_tts_output.mp3")
        
        elapsed = time.time() - start
        file_size = Path(audio_file).stat().st_size
        
        print(f"✅ TTS successful")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Output: {audio_file}")
        print(f"   Size: {file_size:,} bytes")
        
        return True
    except Exception as e:
        print(f"❌ TTS failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tts_streaming():
    """Test 3: Streaming TTS"""
    print("\n" + "="*60)
    print("TEST 3: Streaming TTS")
    print("="*60)
    
    try:
        services = VoiceServices()
        test_text = "Bu streaming TTS testidir. Ses parça parça gelecek."
        
        print(f"Testing streaming TTS with: '{test_text}'")
        start = time.time()
        
        chunks = []
        for chunk in services.synthesize_speech_streaming(test_text):
            chunks.append(chunk)
            if len(chunks) == 1:
                first_chunk_time = time.time() - start
        
        elapsed = time.time() - start
        total_size = sum(len(c) for c in chunks)
        
        print(f"✅ Streaming TTS successful")
        print(f"   First chunk: {first_chunk_time:.2f}s")
        print(f"   Total time: {elapsed:.2f}s")
        print(f"   Chunks: {len(chunks)}")
        print(f"   Total size: {total_size:,} bytes")
        
        return True
    except Exception as e:
        print(f"❌ Streaming TTS failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_llm():
    """Test 4: LLM"""
    print("\n" + "="*60)
    print("TEST 4: Language Model")
    print("="*60)
    
    try:
        services = VoiceServices()
        test_message = "Merhaba, nasılsın?"
        
        print(f"Testing LLM with: '{test_message}'")
        start = time.time()
        
        response = services.generate_response(test_message)
        
        elapsed = time.time() - start
        
        print(f"✅ LLM successful")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Model: {Config.LLM_MODEL}")
        print(f"   Response: {response[:100]}...")
        
        return True
    except Exception as e:
        print(f"❌ LLM failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_async_operations():
    """Test 5: Async Operations"""
    print("\n" + "="*60)
    print("TEST 5: Async Operations")
    print("="*60)
    
    try:
        services = VoiceServices()
        
        # Test async LLM
        print("Testing async LLM...")
        start = time.time()
        response = await services.generate_response_async("Merhaba")
        elapsed = time.time() - start
        
        print(f"✅ Async LLM successful")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Response: {response[:50]}...")
        
        # Test async TTS
        print("\nTesting async TTS...")
        start = time.time()
        audio_data = await services.synthesize_speech_async("Test mesajı")
        elapsed = time.time() - start
        
        print(f"✅ Async TTS successful")
        print(f"   Time: {elapsed:.2f}s")
        print(f"   Size: {len(audio_data):,} bytes")
        
        return True
    except Exception as e:
        print(f"❌ Async operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_latency_benchmark():
    """Test 6: Latency Benchmark"""
    print("\n" + "="*60)
    print("TEST 6: Latency Benchmark")
    print("="*60)
    
    try:
        services = VoiceServices()
        test_message = "Bugün hava nasıl?"
        
        print("Running full pipeline benchmark...")
        print(f"Input: '{test_message}'")
        
        # LLM
        print("\n[1/2] LLM...")
        llm_start = time.time()
        response = services.generate_response(test_message)
        llm_time = time.time() - llm_start
        print(f"      Time: {llm_time:.2f}s")
        print(f"      Response: {response[:50]}...")
        
        # TTS
        print("\n[2/2] TTS...")
        tts_start = time.time()
        audio_file = services.synthesize_speech(response[:100])  # Limit for speed
        tts_time = time.time() - tts_start
        print(f"      Time: {tts_time:.2f}s")
        
        total_time = llm_time + tts_time
        
        print(f"\n✅ Benchmark complete")
        print(f"   LLM: {llm_time:.2f}s")
        print(f"   TTS: {tts_time:.2f}s")
        print(f"   Total (LLM+TTS): {total_time:.2f}s")
        print(f"\n   Note: STT would add ~0.5-1.5s for real conversation")
        print(f"   Estimated full turn latency: {total_time + 1.0:.2f}s")
        
        return True
    except Exception as e:
        print(f"❌ Benchmark failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 Conversational AI - Component Tests")
    print("="*60)
    print("This will test all components without microphone input")
    print()
    
    # Track results
    results = {
        "Configuration": False,
        "TTS": False,
        "Streaming TTS": False,
        "LLM": False,
        "Async Operations": False,
        "Latency Benchmark": False
    }
    
    # Run tests
    results["Configuration"] = test_configuration()
    
    if results["Configuration"]:
        results["TTS"] = test_tts()
        results["Streaming TTS"] = test_tts_streaming()
        results["LLM"] = test_llm()
        results["Async Operations"] = asyncio.run(test_async_operations())
        results["Latency Benchmark"] = test_latency_benchmark()
    else:
        print("\n⚠️  Skipping other tests due to configuration error")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}  {test_name}")
    
    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    print(f"\nTotal: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("\n🎉 All tests passed! System is ready.")
        print("\nRun the conversation system with:")
        print("  python main.py --vad")
    else:
        print("\n⚠️  Some tests failed. Please check configuration and API keys.")
        print("\nTroubleshooting:")
        print("  1. Check .env file has correct API keys")
        print("  2. Verify FAL_KEY at https://fal.ai/dashboard")
        print("  3. Verify OPENROUTER_KEY at https://openrouter.ai/keys")
        print("  4. Check internet connection")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

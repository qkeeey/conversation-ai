"""
Test LLM Provider Configuration
Verify that Gemini API is working correctly
"""
import asyncio
from config import Config
from voice_services_optimized import VoiceServicesOptimized


async def test_llm_provider():
    print("="*70)
    print("🧪 TESTING LLM PROVIDER CONFIGURATION")
    print("="*70)
    
    # Show configuration
    print(f"\n📋 Current Configuration:")
    print(f"  LLM Provider: {Config.LLM_PROVIDER}")
    print(f"  LLM Model: {Config.LLM_MODEL}")
    print(f"  LLM Base URL: {Config.LLM_BASE_URL}")
    print(f"  Temperature: {Config.LLM_TEMPERATURE}")
    print(f"  Max Tokens: {Config.LLM_MAX_TOKENS}")
    
    # Check API keys
    print(f"\n🔑 API Keys:")
    if Config.LLM_PROVIDER == 'gemini':
        if Config.GEMINI_KEY:
            print(f"  GEMINI_KEY: {Config.GEMINI_KEY[:10]}... ✅")
        else:
            print(f"  GEMINI_KEY: NOT SET ❌")
            return
    elif Config.LLM_PROVIDER == 'fal':
        if Config.FAL_KEY:
            print(f"  FAL_KEY: {Config.FAL_KEY[:10]}... ✅")
        else:
            print(f"  FAL_KEY: NOT SET ❌")
            return
    
    # Test LLM streaming
    print(f"\n🚀 Testing LLM Streaming...")
    print(f"  Query: 'Merhaba, nasılsın?'")
    
    service = VoiceServicesOptimized()
    
    try:
        import time
        start_time = time.time()
        first_token_time = None
        full_response = ""
        chunk_count = 0
        
        async for chunk_text, is_final, timing in service.generate_response_streaming_async(
            "Merhaba, nasılsın?",
            []
        ):
            if chunk_text:
                if first_token_time is None:
                    first_token_time = time.time() - start_time
                    print(f"\n  ⚡ First token: {first_token_time*1000:.0f}ms")
                
                full_response += chunk_text
                chunk_count += 1
                print(f"  📝 Chunk {chunk_count}: '{chunk_text}'", end='', flush=True)
            
            if is_final:
                total_time = time.time() - start_time
                break
        
        print(f"\n\n✅ LLM Streaming Test PASSED")
        print(f"\n📊 Results:")
        print(f"  First Token: {first_token_time*1000:.0f}ms")
        print(f"  Total Time: {total_time*1000:.0f}ms")
        print(f"  Chunks: {chunk_count}")
        print(f"  Response Length: {len(full_response)} chars")
        print(f"  Response: \"{full_response}\"")
        
        # Performance assessment
        print(f"\n📈 Performance Assessment:")
        if first_token_time < 1.0:
            print(f"  ⚡ EXCELLENT: First token < 1s")
        elif first_token_time < 1.5:
            print(f"  ✅ GOOD: First token < 1.5s")
        else:
            print(f"  ⚠️  SLOW: First token > 1.5s")
        
        if Config.LLM_PROVIDER == 'gemini':
            print(f"\n✅ Google Gemini Direct API is working!")
            print(f"  Switch back to FAL by setting: LLM_PROVIDER=fal in .env")
        
    except Exception as e:
        print(f"\n❌ LLM Test FAILED: {e}")
        print(f"\n🔧 Troubleshooting:")
        if Config.LLM_PROVIDER == 'gemini':
            print(f"  1. Check GEMINI_KEY is valid")
            print(f"  2. Check model name format: '{Config.LLM_MODEL}'")
            print(f"  3. Try: LLM_MODEL=gemini-2.0-flash-exp")
        print(f"\n  See LLM_PROVIDER_GUIDE.md for details")
    
    finally:
        await service.close()
    
    print("\n" + "="*70)


if __name__ == "__main__":
    asyncio.run(test_llm_provider())

"""Test Recall.ai output_audio API to understand expected format"""
import httpx
import os
import base64
import json

# Load environment
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.split('#')[0].strip()
                    os.environ[key.strip()] = value

load_env()

API_KEY = os.getenv('RECALL_API_KEY')
BASE_URL = os.getenv('RECALL_BASE_URL', 'https://eu-central-1.recall.ai')
BOT_ID = "test-bot-id"  # Replace with actual bot ID if testing

# Create dummy PCM audio (1 second of silence at 16kHz)
sample_rate = 16000
duration_s = 1
pcm_data = b'\x00\x00' * (sample_rate * duration_s)  # 16-bit PCM silence

print("Testing Recall.ai output_audio API")
print(f"Base URL: {BASE_URL}")
print(f"Bot ID: {BOT_ID}")
print(f"PCM data size: {len(pcm_data)} bytes")
print()

# Test different formats
async def test_formats():
    async with httpx.AsyncClient(
        headers={"Authorization": API_KEY},
        timeout=30.0
    ) as client:
        
        # Test 1: JSON with base64
        print("=" * 60)
        print("TEST 1: JSON with base64-encoded PCM")
        print("=" * 60)
        audio_b64 = base64.b64encode(pcm_data).decode('utf-8')
        payload = {
            "audio_data": audio_b64,
            "sample_rate": sample_rate,
            "encoding": "pcm"
        }
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/bot/{BOT_ID}/output_audio",
                json=payload
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        print()
        
        # Test 2: Raw PCM with content-type header
        print("=" * 60)
        print("TEST 2: Raw PCM with Content-Type header")
        print("=" * 60)
        
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/bot/{BOT_ID}/output_audio",
                content=pcm_data,
                headers={"Content-Type": "audio/pcm"}
            )
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        except Exception as e:
            print(f"Error: {e}")
        
        print()
        
        # Test 3: Check API documentation endpoint
        print("=" * 60)
        print("TEST 3: Try OPTIONS to check accepted formats")
        print("=" * 60)
        
        try:
            response = await client.options(
                f"{BASE_URL}/api/v1/bot/{BOT_ID}/output_audio"
            )
            print(f"Status: {response.status_code}")
            print(f"Headers: {dict(response.headers)}")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_formats())

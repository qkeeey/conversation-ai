"""Test Recall.ai API key directly"""
import os
import sys
import httpx

# Manually load .env file
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    # Remove comments
                    value = value.split('#')[0].strip()
                    env_vars[key.strip()] = value
    return env_vars

env = load_env()
RECALL_API_KEY = env.get('RECALL_API_KEY', os.getenv('RECALL_API_KEY'))
RECALL_BASE_URL = env.get('RECALL_BASE_URL', os.getenv('RECALL_BASE_URL', 'https://us-east-1.recall.ai'))

print("="*60)
print("Recall.ai API Key Verification Test")
print("="*60)
print(f"\n📋 Configuration:")
print(f"   API Key: {RECALL_API_KEY[:10]}...{RECALL_API_KEY[-4:] if RECALL_API_KEY else 'NOT SET'}")
print(f"   Base URL: {RECALL_BASE_URL}")
print()

if not RECALL_API_KEY:
    print("❌ RECALL_API_KEY is not set in .env file")
    sys.exit(1)

async def test_api_key():
    """Test API key by listing bots"""
    print("🔍 Testing API key with Recall.ai format (no Bearer/Token prefix)...\n")
    
    client = httpx.AsyncClient(
        headers={
            "Authorization": RECALL_API_KEY,
            "Content-Type": "application/json"
        },
        timeout=10.0
    )
    
    try:
        response = await client.get(f"{RECALL_BASE_URL}/api/v1/bot")
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API Key is VALID!")
            bots = response.json()
            print(f"   Found {len(bots.get('data', []))} bot(s)")
            return True
        elif response.status_code == 401:
            print("❌ API Key is INVALID or EXPIRED")
            print(f"Response: {response.text}")
            return False
        else:
            print(f"⚠️  Unexpected status: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        await client.aclose()

# Run test
import asyncio
if __name__ == "__main__":
    result = asyncio.run(test_api_key())
    
    print("\n" + "="*60)
    if result:
        print("✅ Recall.ai API key is working!")
        print("\n💡 The correct format is:")
        print('   "Authorization": api_key  (no Bearer/Token prefix)')
    else:
        print("❌ API key verification failed!")
        print("\n📋 Please verify your API key:")
        print("   1. Go to https://recall.ai/dashboard")
        print("   2. Navigate to Settings > API Keys")
        print("   3. Verify the key is active and has permissions")
        print("   4. Create a new key if needed")
        print("   5. Update RECALL_API_KEY in .env file")
        print("\n   Current key: " + (RECALL_API_KEY[:10] + "..." + RECALL_API_KEY[-4:] if RECALL_API_KEY else "NOT SET"))
    print("="*60)
    
    sys.exit(0 if result else 1)

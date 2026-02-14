"""Test script for bot lifecycle and webhook simulation"""
# -*- coding: utf-8 -*-
import requests
import json
import time
import os
import sys
import hmac
import hashlib
from datetime import datetime, timezone

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Load environment variables
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
    print(f"[DEBUG] Loading .env from: {env_path}")
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    value = value.split('#')[0].strip()
                    key = key.strip()
                    if key == 'TEST_MEETING_URL':
                        print(f"[DEBUG] Found TEST_MEETING_URL: {value}")
                    os.environ[key] = value
    else:
        print(f"[DEBUG] .env file not found at {env_path}")

load_env()

BASE_URL = "http://localhost:8000"
TEST_MEETING_URL = os.getenv('TEST_MEETING_URL', 'https://us05web.zoom.us/j/82967849526?pwd=CTxfwXigWx4Hh9yZwXVS6DVdBD4Kn4.1')
WEBHOOK_SECRET = os.getenv('RECALL_WEBHOOK_SECRET')
print(f"[DEBUG] Loaded TEST_MEETING_URL: {TEST_MEETING_URL}")
print(f"[DEBUG] Webhook secret configured: {bool(WEBHOOK_SECRET)}")
print()

def compute_webhook_signature(body: bytes) -> str:
    """Compute HMAC-SHA256 signature for webhook request"""
    if not WEBHOOK_SECRET:
        return None
    return hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()

def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200, "Health check failed"
    print("✅ Health check passed")


def test_create_bot():
    """Test bot creation"""
    print("\n" + "="*60)
    print("TEST 2: Create Bot")
    print("="*60)
    
    payload = {
        "meeting_url": TEST_MEETING_URL,
        "bot_name": "Freya",
        "metadata": {
            "test": True,
            "created_by": "test_script"
        }
    }
    
    print(f"Using meeting URL: {TEST_MEETING_URL}")
    
    print(f"Request: POST /v1/bots")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    response = requests.post(f"{BASE_URL}/v1/bots", json=payload)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 201:
        bot_id = response.json()["bot_id"]
        print(f"✅ Bot created with ID: {bot_id}")
        return bot_id
    else:
        print(f"⚠️  Bot creation returned status {response.status_code}")
        print(f"   This is expected if Recall API key is not configured")
        return None


def test_get_bot(bot_id):
    """Test getting bot details"""
    print("\n" + "="*60)
    print(f"TEST 3: Get Bot {bot_id[:8]}...")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/v1/bots/{bot_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200, "Get bot failed"
    print("✅ Get bot passed")


def test_simulate_transcript(bot_id):
    """Test simulating a transcript webhook"""
    print("\n" + "="*60)
    print("TEST 4: Simulate Transcript Webhook")
    print("="*60)
    
    payload = {
        "bot_id": bot_id,
        "event": "transcript.data",
        "participant": {
            "id": "user_123",
            "name": "Alice"
        },
        "text": "Freya, hello! How are you?",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    print(f"Request: POST /webhooks/recall/realtime")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    # Compute webhook signature
    body = json.dumps(payload).encode()
    signature = compute_webhook_signature(body)
    headers = {"Content-Type": "application/json"}
    if signature:
        headers["X-Recall-Signature"] = signature
        print(f"Signature: {signature[:32]}...")
    
    response = requests.post(
        f"{BASE_URL}/webhooks/recall/realtime", 
        data=body,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200, "Webhook simulation failed"
    print("✅ Transcript webhook simulated")
    print("   Check agent-worker logs to see if it's processing...")


def test_simulate_status_webhook(bot_id):
    """Test simulating a status change webhook"""
    print("\n" + "="*60)
    print("TEST 5: Simulate Status Change Webhook")
    print("="*60)
    
    payload = {
        "bot_id": bot_id,
        "status": "in_call",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    print(f"Request: POST /webhooks/recall/status")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    
    # Compute webhook signature
    body = json.dumps(payload).encode()
    signature = compute_webhook_signature(body)
    headers = {"Content-Type": "application/json"}
    if signature:
        headers["X-Recall-Signature"] = signature
        print(f"Signature: {signature[:32]}...")
    
    response = requests.post(
        f"{BASE_URL}/webhooks/recall/status",
        data=body,
        headers=headers
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    assert response.status_code == 200, "Status webhook simulation failed"
    print("✅ Status webhook simulated")


def test_list_bots():
    """Test listing all bots"""
    print("\n" + "="*60)
    print("TEST 6: List All Bots")
    print("="*60)
    
    response = requests.get(f"{BASE_URL}/v1/bots")
    print(f"Status: {response.status_code}")
    data = response.json()
    print(f"Total bots: {data['total']}")
    
    for bot in data['bots'][:3]:  # Show first 3
        print(f"  - {bot['bot_id'][:8]}... | {bot['status']} | {bot['meeting_url']}")
    
    assert response.status_code == 200, "List bots failed"
    print("✅ List bots passed")


def test_stop_bot(bot_id):
    """Test stopping a bot"""
    print("\n" + "="*60)
    print(f"TEST 7: Stop Bot {bot_id[:8]}...")
    print("="*60)
    
    response = requests.delete(f"{BASE_URL}/v1/bots/{bot_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    if response.status_code == 200:
        print(f"✅ Bot stopped")
        
        # Verify bot is marked as stopped
        print(f"\nVerifying bot status after stop...")
        get_response = requests.get(f"{BASE_URL}/v1/bots/{bot_id}")
        if get_response.status_code == 200:
            bot_data = get_response.json()
            print(f"Bot status: {bot_data['status']}")
            if bot_data['status'] == 'stopped':
                print(f"✅ Bot correctly marked as 'stopped' in database")
            else:
                print(f"⚠️  Bot status is '{bot_data['status']}' instead of 'stopped'")
        
        # Check bot list to confirm
        print(f"\nSearching for bot in list...")
        list_response = requests.get(f"{BASE_URL}/v1/bots")
        if list_response.status_code == 200:
            bots = list_response.json()['bots']
            bot_in_list = next((b for b in bots if b['bot_id'] == bot_id), None)
            if bot_in_list:
                print(f"Found bot in list with status: {bot_in_list['status']}")
            else:
                print(f"⚠️  Bot not found in list")
    else:
        print(f"⚠️  Stop bot returned status {response.status_code}")


def main():
    """Run all tests"""
    print("🧪 Bot Orchestrator Integration Tests")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    
    try:
        # Test 1: Health check
        test_health()
        
        # Test 2: Create bot
        bot_id = test_create_bot()
        
        if bot_id:
            # Test 3: Get bot
            test_get_bot(bot_id)
            
            # Test 4: Simulate transcript
            test_simulate_transcript(bot_id)
            
            # Test 5: Simulate status change
            test_simulate_status_webhook(bot_id)
            
            # Wait a bit for processing
            print("\n⏳ Waiting 3 seconds for processing...")
            time.sleep(3)
            
            # Test 6: List bots
            test_list_bots()
            
            # Test 7: Stop bot
            test_stop_bot(bot_id)
        else:
            print("\n⚠️  Skipping bot-specific tests (no bot ID)")
            
            # Still test list bots
            test_list_bots()
        
        print("\n" + "="*60)
        print("🎉 All tests completed!")
        print("="*60)
    
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

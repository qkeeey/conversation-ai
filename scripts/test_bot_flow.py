"""Test script for bot lifecycle and webhook simulation"""
import requests
import json
import time
from datetime import datetime, timezone
import sys


BASE_URL = "http://localhost:8000"


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
        "meeting_url": "https://meet.google.com/test-meeting-xyz",
        "bot_name": "Freya",
        "metadata": {
            "test": True,
            "created_by": "test_script"
        }
    }
    
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
    
    response = requests.post(f"{BASE_URL}/webhooks/recall/realtime", json=payload)
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
    
    response = requests.post(f"{BASE_URL}/webhooks/recall/status", json=payload)
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

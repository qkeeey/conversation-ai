"""Simulate a realistic meeting conversation"""
import requests
import json
import time
from datetime import datetime, timezone
import sys


BASE_URL = "http://localhost:8000"


def create_test_bot():
    """Create a test bot"""
    payload = {
        "meeting_url": "https://meet.google.com/simulated-meeting",
        "bot_name": "Freya",
        "metadata": {"simulation": True}
    }
    
    response = requests.post(f"{BASE_URL}/v1/bots", json=payload)
    if response.status_code == 201:
        bot_id = response.json()["bot_id"]
        print(f"✅ Created bot: {bot_id}")
        return bot_id
    else:
        print(f"❌ Failed to create bot: {response.status_code}")
        return None


def send_transcript(bot_id, participant_name, text):
    """Send a transcript event"""
    payload = {
        "bot_id": bot_id,
        "event": "transcript.data",
        "participant": {
            "id": f"user_{participant_name.lower()}",
            "name": participant_name
        },
        "text": text,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    
    response = requests.post(f"{BASE_URL}/webhooks/recall/realtime", json=payload)
    print(f"📝 {participant_name}: {text}")
    print(f"   → Status: {response.status_code}")


def simulate_meeting(bot_id):
    """Simulate a realistic meeting conversation"""
    print("\n" + "="*60)
    print("🎬 SIMULATING MEETING CONVERSATION")
    print("="*60)
    
    conversation = [
        ("Alice", "Hello everyone, let's start the meeting.", 1),
        ("Bob", "Hi Alice, I'm here.", 2),
        ("Alice", "Freya, can you introduce yourself?", 3),  # Wake word!
        ("Freya", "Hello! I'm simulating a bot response.", 5),  # Bot (should be ignored)
        ("Bob", "That's great. Freya, what features do you have?", 7),  # Wake word!
        ("Alice", "We should discuss the project timeline.", 10),  # No wake word
        ("Bob", "Freya, can you summarize what we discussed so far?", 12),  # Wake word!
        ("Alice", "Great summary! Let's move to the next topic.", 15),  # No wake word
        ("Bob", "Freya, thank you for your help.", 17),  # Wake word!
    ]
    
    for participant, text, delay in conversation:
        time.sleep(delay)
        send_transcript(bot_id, participant, text)
        
        # Give agent time to process
        time.sleep(2)
    
    print("\n✅ Meeting simulation complete")


def main():
    """Run meeting simulation"""
    print("🎬 Meeting Simulation Script")
    print(f"Target: {BASE_URL}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    
    try:
        # Create bot
        bot_id = create_test_bot()
        if not bot_id:
            print("❌ Cannot proceed without bot ID")
            sys.exit(1)
        
        # Simulate meeting
        simulate_meeting(bot_id)
        
        # Wait for final processing
        print("\n⏳ Waiting 10 seconds for final processing...")
        time.sleep(10)
        
        # Stop bot
        print("\n🛑 Stopping bot...")
        response = requests.delete(f"{BASE_URL}/v1/bots/{bot_id}")
        print(f"   Status: {response.status_code}")
        
        print("\n🎉 Simulation complete!")
        print("\n💡 Check agent-worker logs to see:")
        print("   - Which messages triggered responses (wake word detection)")
        print("   - TTFA metrics for each response")
        print("   - TTS chunk generation details")
    
    except Exception as e:
        print(f"\n❌ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

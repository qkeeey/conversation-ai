"""Stop a Recall.ai bot and leave meeting"""
import requests
import sys

BASE_URL = "http://localhost:8000"


def stop_bot(bot_id: str):
    """Stop bot and leave meeting"""
    print(f"🛑 Stopping bot: {bot_id}")
    
    try:
        response = requests.delete(
            f"{BASE_URL}/v1/bots/{bot_id}",
            timeout=30
        )
        
        if response.status_code == 200:
            print("✅ Bot stopped successfully!")
            print(f"   {response.json().get('message', '')}")
            return True
        else:
            print(f"❌ Failed to stop bot: HTTP {response.status_code}")
            print(f"   Error: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is the orchestrator running?")
        print("   Start it with: docker-compose up")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/stop_bot.py <bot_id>")
        print()
        print("Example:")
        print("  python scripts/stop_bot.py a98d996d-57b1-4033-b9f3-a709f133336b")
        print()
        print("Tip: List active bots with: python scripts/create_bot.py --list")
        sys.exit(1)
    
    bot_id = sys.argv[1]
    stop_bot(bot_id)

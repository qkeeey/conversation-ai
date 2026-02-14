"""Create a Recall.ai bot for a meeting"""
import requests
import sys
import os
from datetime import datetime

# Load environment variables
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

BASE_URL = "http://localhost:8000"
BOT_NAME = os.getenv("BOT_NAME", "Freya")
TEST_MEETING_URL = os.getenv("TEST_MEETING_URL", "")


def create_bot(meeting_url: str, bot_name: str = None):
    """Create a new bot and join meeting"""
    if bot_name is None:
        bot_name = BOT_NAME
    
    payload = {
        "meeting_url": meeting_url,
        "bot_name": bot_name,
        "metadata": {
            "created_by": "create_bot.py",
            "created_at": datetime.utcnow().isoformat()
        }
    }
    
    print(f"🔄 Creating bot '{bot_name}' for meeting: {meeting_url}")
    print(f"📡 Using webhook URL: {os.getenv('PUBLIC_BASE_URL', 'Not configured')}")
    print()
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/bots",
            json=payload,
            timeout=30
        )
        
        if response.status_code == 201:
            data = response.json()
            bot_id = data["bot_id"]
            
            print("✅ Bot created successfully!")
            print(f"   Bot ID: {bot_id}")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Meeting: {data['meeting_url']}")
            print()
            print("🎤 The bot will join the meeting shortly.")
            print(f"💬 Say '{bot_name}, hello!' in the meeting to test.")
            print()
            print(f"📊 Monitor logs: docker-compose logs -f agent-worker")
            print(f"🛑 Stop bot: python scripts/stop_bot.py {bot_id}")
            print()
            
            return data
        else:
            print(f"❌ Failed to create bot: HTTP {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed. Is the orchestrator running?")
        print("   Start it with: docker-compose up")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def get_bot(bot_id: str):
    """Get bot details"""
    try:
        response = requests.get(f"{BASE_URL}/v1/bots/{bot_id}")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        print(f"❌ Error getting bot: {e}")
        return None


def list_bots():
    """List all bots"""
    try:
        response = requests.get(f"{BASE_URL}/v1/bots")
        if response.status_code == 200:
            data = response.json()
            print(f"📋 Active bots: {data['total']}")
            for bot in data['bots']:
                print(f"   • {bot['bot_id'][:8]}... - {bot['status']} - {bot['meeting_url']}")
            return data
        return None
    except Exception as e:
        print(f"❌ Error listing bots: {e}")
        return None


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # If TEST_MEETING_URL is set, use it as default
        if TEST_MEETING_URL:
            print("📋 Using TEST_MEETING_URL from .env")
            print()
            create_bot(TEST_MEETING_URL)
        else:
            print("Usage:")
            print("  Create bot:  python scripts/create_bot.py [meeting_url] [bot_name]")
            print("  List bots:   python scripts/create_bot.py --list")
            print()
            print("Examples:")
            print("  python scripts/create_bot.py https://meet.google.com/abc-defg-hij")
            print("  python scripts/create_bot.py https://zoom.us/j/123456789 CustomBot")
            print("  python scripts/create_bot.py --list")
            print()
            print("Tip: Set TEST_MEETING_URL in .env to use without arguments")
            sys.exit(1)
    elif sys.argv[1] == "--list":
        list_bots()
    else:
        meeting_url = sys.argv[1]
        bot_name = sys.argv[2] if len(sys.argv) > 2 else None
        create_bot(meeting_url, bot_name)

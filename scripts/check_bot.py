"""Check bot configuration from Recall.ai API"""
import requests
import sys
import os
import json

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

RECALL_API_KEY = os.getenv("RECALL_API_KEY")
RECALL_BASE_URL = os.getenv("RECALL_BASE_URL", "https://us-east-1.recall.ai")

def check_bot(bot_id: str):
    """Get bot details from Recall API"""
    print(f"🔍 Checking bot configuration: {bot_id}\n")
    
    try:
        response = requests.get(
            f"{RECALL_BASE_URL}/api/v1/bot/{bot_id}",
            headers={"Authorization": RECALL_API_KEY},
            timeout=10
        )
        
        if response.status_code == 200:
            bot_data = response.json()
            print("✅ Bot found!\n")
            print(json.dumps(bot_data, indent=2))
            print("\n" + "="*70)
            
            # Check critical fields
            print("\n🔍 Webhook Configuration:")
            rt_config = bot_data.get("real_time_transcription", {})
            if rt_config:
                print(f"   ✅ Real-time transcription: ENABLED")
                print(f"   📡 Destination URL: {rt_config.get('destination_url', 'Not set')}")
                print(f"   🔧 Partial results: {rt_config.get('partial_results', False)}")
            else:
                print(f"   ❌ Real-time transcription: NOT CONFIGURED")
                print(f"   ⚠️  This is why no transcripts are being sent!")
                print(f"\n💡 Solution:")
                print(f"   1. Make sure PUBLIC_BASE_URL is set in .env")
                print(f"   2. Make sure ngrok is running: ngrok http 8000")
                print(f"   3. Recreate the bot: python scripts/create_bot.py")
            
            print(f"\n📊 Bot Status:")
            print(f"   Status: {bot_data.get('status_changes', [{}])[-1].get('code', 'unknown')}")
            print(f"   Meeting URL: {bot_data.get('meeting_url', 'N/A')}")
            
            return bot_data
        else:
            print(f"❌ Failed to get bot: HTTP {response.status_code}")
            print(f"   Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


def list_recent_bots():
    """List recent bots from local database"""
    try:
        import sqlite3
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bots.db')
        
        if not os.path.exists(db_path):
            print("❌ No local database found")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT bot_id, meeting_url, status, created_at 
            FROM bots 
            ORDER BY created_at DESC 
            LIMIT 5
        """)
        
        bots = cursor.fetchall()
        conn.close()
        
        if bots:
            print("\n📋 Recent bots from database:")
            for bot_id, meeting_url, status, created_at in bots:
                print(f"   • {bot_id[:8]}... - {status} - {created_at}")
            print(f"\n💡 Check any bot with: python scripts/check_bot.py <bot_id>")
        else:
            print("No bots found in database")
            
    except Exception as e:
        print(f"⚠️  Could not read local database: {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_bot.py <bot_id>")
        print("\nExample:")
        print("  python scripts/check_bot.py eafac8fc-612c-4281-9c4a-3b6437a32535")
        print()
        list_recent_bots()
        sys.exit(1)
    
    bot_id = sys.argv[1]
    check_bot(bot_id)

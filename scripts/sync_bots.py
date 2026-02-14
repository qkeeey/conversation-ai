"""Sync local database with actual Recall.ai bot statuses"""
import requests
import os
import sqlite3
import sys

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


def get_bot_from_recall(bot_id: str):
    """Get bot details from Recall API"""
    try:
        response = requests.get(
            f"{RECALL_BASE_URL}/api/v1/bot/{bot_id}",
            headers={"Authorization": RECALL_API_KEY},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            status_changes = data.get('status_changes', [])
            if status_changes:
                current_status = status_changes[-1].get('code', 'unknown')
                return current_status, True
            return 'unknown', True
        elif response.status_code == 404:
            return 'not_found', False
        else:
            return 'error', False
    except Exception:
        return 'error', False


def sync_database():
    """Sync local database with Recall API"""
    print("🔄 Syncing local database with Recall.ai...\n")
    
    db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bots.db')
    
    if not os.path.exists(db_path):
        print("❌ No database found")
        return
    
    # Get all bots from DB
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT bot_id, status FROM bots ORDER BY created_at DESC")
    db_bots = cursor.fetchall()
    
    if not db_bots:
        print("✅ No bots in database")
        conn.close()
        return
    
    print(f"📋 Found {len(db_bots)} bots in database\n")
    
    updated = 0
    not_found = 0
    errors = 0
    
    for i, (bot_id, db_status) in enumerate(db_bots, 1):
        print(f"[{i}/{len(db_bots)}] {bot_id[:8]}... (DB: {db_status})", end=" → ")
        
        # Get actual status from Recall
        recall_status, exists = get_bot_from_recall(bot_id)
        
        if not exists and recall_status == 'not_found':
            print(f"❌ Not found on Recall")
            # Update to 'done' since it doesn't exist anymore
            cursor.execute("UPDATE bots SET status = 'done' WHERE bot_id = ?", (bot_id,))
            not_found += 1
        elif recall_status == 'error':
            print(f"⚠️  Error checking")
            errors += 1
        else:
            print(f"Recall: {recall_status}")
            
            # Update if different
            if recall_status != db_status:
                cursor.execute("UPDATE bots SET status = ? WHERE bot_id = ?", (recall_status, bot_id))
                updated += 1
    
    conn.commit()
    conn.close()
    
    print("\n" + "="*70)
    print(f"📊 Sync Results:")
    print(f"   ✅ Updated: {updated}")
    print(f"   ❌ Not found on Recall: {not_found}")
    print(f"   ⚠️  Errors: {errors}")
    print(f"   Total: {len(db_bots)}")
    print("="*70)
    
    print("\n💡 Now list bots to see actual status:")
    print("   python scripts/create_bot.py --list")


if __name__ == "__main__":
    sync_database()

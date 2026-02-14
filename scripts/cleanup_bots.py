"""Stop and clean up all bots"""
import requests
import sys
import os
import sqlite3
import time

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
RECALL_API_KEY = os.getenv("RECALL_API_KEY")
RECALL_BASE_URL = os.getenv("RECALL_BASE_URL", "https://us-east-1.recall.ai")


def get_all_bots():
    """Get all bots from local database"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bots.db')
        
        if not os.path.exists(db_path):
            print("❌ No local database found")
            return []
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT bot_id, meeting_url, status, created_at 
            FROM bots 
            ORDER BY created_at DESC
        """)
        
        bots = cursor.fetchall()
        conn.close()
        
        return [{"bot_id": b[0], "meeting_url": b[1], "status": b[2], "created_at": b[3]} for b in bots]
            
    except Exception as e:
        print(f"❌ Error reading database: {e}")
        return []


def stop_bot_via_api(bot_id: str):
    """Stop bot via local orchestrator API"""
    try:
        response = requests.delete(
            f"{BASE_URL}/v1/bots/{bot_id}",
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "Stopped via API"
        elif response.status_code == 404:
            return True, "Already removed"
        else:
            return False, f"HTTP {response.status_code}"
            
    except Exception as e:
        return False, str(e)


def update_bot_status_in_db(bot_id: str, status: str):
    """Update bot status in local database"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bots.db')
        
        if not os.path.exists(db_path):
            return False
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE bots SET status = ? WHERE bot_id = ?", (status, bot_id))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def get_bot_status_from_recall(bot_id: str):
    """Get bot's actual status from Recall API"""
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
                return current_status
            return 'unknown'
        elif response.status_code == 404:
            return 'not_found'
        else:
            return 'error'
    except Exception:
        return 'error'


def stop_bot_direct(bot_id: str):
    """Stop bot directly via Recall API (if orchestrator fails)"""
    try:
        # First check if bot exists and is in a stoppable state
        status = get_bot_status_from_recall(bot_id)
        
        if status == 'not_found':
            return True, "Bot no longer exists on Recall"
        
        if status in ['done', 'fatal', 'already_left']:
            return True, f"Bot already finished (status: {status})"
        
        # Try to stop it
        response = requests.post(
            f"{RECALL_BASE_URL}/api/v1/bot/{bot_id}/leave_call/",
            headers={"Authorization": RECALL_API_KEY},
            timeout=10
        )
        
        if response.status_code == 200:
            return True, "Stopped via Recall API"
        elif response.status_code == 404:
            return True, "Bot not found (already removed)"
        elif response.status_code == 400:
            # 400 usually means bot is already stopped or can't be stopped
            return True, f"Bot can't be stopped (status: {status}) - marking as done"
        else:
            return False, f"HTTP {response.status_code}: {response.text[:100]}"
            
    except Exception as e:
        return False, str(e)


def cleanup_all_bots(dry_run=False):
    """Stop all bots"""
    print("🔍 Finding all bots...\n")
    
    bots = get_all_bots()
    
    if not bots:
        print("✅ No bots found in database")
        return
    
    print(f"📋 Found {len(bots)} bots\n")
    
    # Group by status
    active_bots = [b for b in bots if b['status'] not in ['stopped', 'done', 'fatal']]
    inactive_bots = [b for b in bots if b['status'] in ['stopped', 'done', 'fatal']]
    
    print(f"   🟢 Active bots: {len(active_bots)}")
    print(f"   🔴 Already stopped: {len(inactive_bots)}")
    print()
    
    if dry_run:
        print("🔍 DRY RUN - No bots will be stopped\n")
        print("Active bots that would be stopped:")
        for bot in active_bots:
            print(f"   • {bot['bot_id'][:8]}... - {bot['status']}")
        print(f"\n💡 Run without --dry-run to actually stop them")
        return
    
    if not active_bots:
        print("✅ All bots are already stopped")
        return
    
    print(f"🛑 Stopping {len(active_bots)} active bots...\n")
    
    stopped_count = 0
    failed_count = 0
    
    for i, bot in enumerate(active_bots, 1):
        bot_id = bot['bot_id']
        status = bot['status']
        
        print(f"[{i}/{len(active_bots)}] {bot_id[:8]}... (DB status: {status})")
        
        # Check actual status on Recall first
        recall_status = get_bot_status_from_recall(bot_id)
        print(f"   📡 Recall status: {recall_status}")
        
        if recall_status in ['done', 'fatal', 'not_found', 'already_left']:
            print(f"   ✅ Bot already finished on Recall")
            update_bot_status_in_db(bot_id, 'stopped')
            stopped_count += 1
        else:
            # Try orchestrator API first
            success, message = stop_bot_via_api(bot_id)
            
            if not success:
                # Fallback to direct Recall API
                print(f"   ⚠️  API failed: {message}, trying Recall directly...")
                success, message = stop_bot_direct(bot_id)
            
            if success:
                print(f"   ✅ {message}")
                update_bot_status_in_db(bot_id, 'stopped')
                stopped_count += 1
            else:
                print(f"   ❌ Failed: {message}")
                failed_count += 1
        
        # Rate limiting
        if i < len(active_bots):
            time.sleep(0.3)
    
    print("\n" + "="*70)
    print(f"📊 Results:")
    print(f"   ✅ Stopped: {stopped_count}")
    print(f"   ❌ Failed: {failed_count}")
    print(f"   Total bots: {len(bots)}")
    print("="*70)


def clear_database():
    """Clear all bots from local database"""
    try:
        db_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'bots.db')
        
        if not os.path.exists(db_path):
            print("❌ No database to clear")
            return
        
        response = input("\n⚠️  Clear all bot records from database? This cannot be undone! (yes/no): ")
        
        if response.lower() != 'yes':
            print("❌ Database clear cancelled")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bots")
        cursor.execute("DELETE FROM events")
        deleted_bots = cursor.rowcount
        conn.commit()
        conn.close()
        
        print(f"✅ Cleared {deleted_bots} bot records from database")
        
    except Exception as e:
        print(f"❌ Error clearing database: {e}")


if __name__ == "__main__":
    print("🧹 Bot Cleanup Utility\n")
    print("="*70)
    
    # Parse arguments
    dry_run = "--dry-run" in sys.argv
    clear_db = "--clear-db" in sys.argv
    
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python scripts/cleanup_bots.py [options]")
        print()
        print("Options:")
        print("  --dry-run     Show what would be stopped without actually stopping")
        print("  --clear-db    Clear all bot records from database after stopping")
        print("  --help, -h    Show this help message")
        print()
        print("Examples:")
        print("  python scripts/cleanup_bots.py")
        print("  python scripts/cleanup_bots.py --dry-run")
        print("  python scripts/cleanup_bots.py --clear-db")
        sys.exit(0)
    
    # Stop all bots
    cleanup_all_bots(dry_run=dry_run)
    
    # Optionally clear database
    if clear_db and not dry_run:
        clear_database()
    
    print("\n✅ Cleanup complete!")

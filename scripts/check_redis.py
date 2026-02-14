"""Check Redis queue status"""
import redis
import json
import sys


def check_redis():
    """Check Redis connection and queue status"""
    print("🔍 Redis Queue Status Check\n")
    
    try:
        # Connect to Redis
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        
        # Test connection
        r.ping()
        print("✅ Connected to Redis")
        
        # Check queue length
        queue_length = r.llen('meeting_events')
        print(f"📊 Queue 'meeting_events': {queue_length} items")
        
        # Show queue items
        if queue_length > 0:
            print("\n📋 Queue items:")
            items = r.lrange('meeting_events', 0, min(queue_length, 10) - 1)
            
            for i, item in enumerate(items, 1):
                try:
                    data = json.loads(item)
                    print(f"\n  {i}. Type: {data.get('type')}")
                    print(f"     Bot ID: {data.get('bot_id', 'N/A')[:12]}...")
                    print(f"     Participant: {data.get('participant', {}).get('name', 'N/A')}")
                    print(f"     Text: {data.get('text', 'N/A')[:60]}...")
                except json.JSONDecodeError:
                    print(f"\n  {i}. Invalid JSON: {item[:100]}...")
        else:
            print("   (empty)")
        
        # Check session keys
        session_keys = r.keys('session:*')
        print(f"\n🗄️  Active sessions: {len(session_keys)}")
        
        # Check speaking state keys
        speaking_keys = r.keys('bot:speaking:*')
        print(f"🗣️  Bots currently speaking: {len(speaking_keys)}")
        
        print("\n✅ Redis check complete")
    
    except redis.ConnectionError:
        print("❌ Failed to connect to Redis")
        print("   Make sure Redis is running: docker-compose up redis")
        sys.exit(1)
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    check_redis()

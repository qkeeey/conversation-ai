"""Agent Worker Service - Main entry point"""
import sys
import os
import asyncio
from datetime import datetime

# Add paths for Docker volume mounts
sys.path.append('/src')
sys.path.append('/bot-orchestrator')

from dotenv import load_dotenv
load_dotenv('/src/.env')

from redis_queue import RedisQueue
from session_manager import SessionManager
from turn_manager import TurnManager
from processor import EventProcessor


async def main():
    """Main event loop - consume from Redis queue and process"""
    print("🚀 Starting Agent Worker Service...")
    print(f"📅 {datetime.utcnow().isoformat()}")
    
    # Initialize components
    redis_queue = RedisQueue()
    await redis_queue.connect()
    print("✅ Connected to Redis queue")
    
    session_manager = SessionManager()
    await session_manager.connect()
    print("✅ Session manager initialized")
    
    bot_name = os.getenv("BOT_NAME", "Freya")
    turn_manager = TurnManager(bot_name=bot_name)
    await turn_manager.connect()
    print(f"✅ Turn manager initialized (wake word: '{bot_name}')")
    
    # Import meeting conversation engine (will be created in next task)
    try:
        from conversation_engine_meeting import MeetingConversationEngine
        meeting_engine = MeetingConversationEngine(redis_queue=redis_queue)
        print("✅ Meeting conversation engine initialized")
    except ImportError:
        print("⚠️  Meeting conversation engine not found, using placeholder")
        meeting_engine = None
    
    processor = EventProcessor(
        session_manager=session_manager,
        turn_manager=turn_manager,
        meeting_engine=meeting_engine
    )
    print("✅ Event processor initialized")
    
    print("\n🎧 Listening for transcript events...")
    print("   (Press Ctrl+C to stop)\n")
    
    try:
        # Main event loop
        while True:
            # Blocking pop from Redis queue (1 second timeout)
            event = await redis_queue.dequeue_transcript(timeout=1)
            
            if event:
                message_id = event.get("message_id", "unknown")
                bot_id = event.get("bot_id", "unknown")
                text = event.get("text", "")
                print(f"\n📬 [DEQUEUE] msg_id={message_id}, bot={bot_id[:8] if len(bot_id) > 8 else bot_id}")
                print(f"📬 [DEQUEUE] Raw event (first 300 chars): {str(event)[:300]}")
                print(f"📬 [DEQUEUE] Text: '{text}'\n")
                
                # Process event
                await processor.process_event(event)
            else:
                # Timeout - just loop again
                pass
    
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down gracefully...")
    
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        print("🧹 Cleaning up...")
        await redis_queue.close()
        await session_manager.close()
        await turn_manager.close()
        print("✅ Agent worker stopped")


if __name__ == "__main__":
    asyncio.run(main())

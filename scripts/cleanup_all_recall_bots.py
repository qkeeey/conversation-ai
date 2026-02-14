"""Clean up ALL bots from Recall.ai API (not just database)"""
import os
import sys
import asyncio
import httpx

async def main():
    """List and stop ALL bots from Recall API"""
    api_key = os.getenv("RECALL_API_KEY")
    base_url = os.getenv("RECALL_BASE_URL", "https://us-east-1.recall.ai").rstrip("/")
    
    if not api_key:
        print("❌ RECALL_API_KEY not set")
        return
    
    client = httpx.AsyncClient(
        headers={
            "Authorization": api_key,
            "Content-Type": "application/json"
        },
        timeout=30.0
    )
    
    try:
        # List ALL bots from Recall
        print("📋 Fetching all bots from Recall API...")
        response = await client.get(f"{base_url}/api/v1/bot/")
        response.raise_for_status()
        
        bots_data = response.json()
        bots = bots_data.get("results", [])
        
        if not bots:
            print("✅ No bots found in Recall")
            return
        
        print(f"\\n🤖 Found {len(bots)} bot(s) in Recall:")
        for bot in bots:
            bot_id = bot.get("id")
            status = bot.get("status_changes", [{}])[-1].get("code", "unknown") if bot.get("status_changes") else "unknown"
            meeting_url = bot.get("meeting_url", "")[:60]
            print(f"   • {bot_id} | Status: {status} | Meeting: {meeting_url}...")
        
        # Ask for confirmation
        print(f"\\n⚠️  This will stop ALL {len(bots)} bots!")
        confirm = input("Continue? (yes/no): ")
        
        if confirm.lower() != "yes":
            print("❌ Cancelled")
            return
        
        # Stop all bots
        print(f"\\n🛑 Stopping {len(bots)} bots...")
        for bot in bots:
            bot_id = bot.get("id")
            try:
                response = await client.post(f"{base_url}/api/v1/bot/{bot_id}/leave_call/")
                if response.status_code in [200, 204]:
                    print(f"   ✅ Stopped {bot_id}")
                elif response.status_code == 404:
                    print(f"   ⚠️  Bot {bot_id} already gone")
                else:
                    print(f"   ❌ Failed to stop {bot_id}: {response.status_code}")
            except Exception as e:
                print(f"   ❌ Error stopping {bot_id}: {e}")
        
        print("\\n🎉 Cleanup complete!")
        
    except httpx.HTTPStatusError as e:
        print(f"❌ HTTP error: {e}")
        print(f"   Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.aclose()

if __name__ == "__main__":
    asyncio.run(main())

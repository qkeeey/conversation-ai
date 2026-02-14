#!/usr/bin/env python3
"""Check bot status and Output Media configuration in Recall API"""
import os
import sys
import requests
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

def check_bot(bot_id: str):
    """Get detailed bot status from Recall"""
    api_key = os.getenv("RECALL_API_KEY")
    if not api_key:
        print("❌ RECALL_API_KEY not set")
        return
    
    base_url = os.getenv("RECALL_BASE_URL", "https://us-east-1.recall.ai")
    headers = {"Authorization": api_key}
    
    # Get bot details
    print(f"🔍 Fetching bot: {bot_id}")
    r = requests.get(f"{base_url}/api/v1/bot/{bot_id}", headers=headers, timeout=30)
    if r.status_code != 200:
        print(f"❌ Error: {r.status_code}")
        print(r.text)
        return
    
    bot = r.json()
    
    print(f"\n{'='*70}")
    print(f"Bot ID: {bot.get('id')}")
    print(f"Status: {bot.get('status_changes', [{}])[-1].get('code', 'unknown')}")
    meeting_url = bot.get('meeting_url') or ''
    print(f"Meeting URL: {meeting_url[:60] if meeting_url else 'Not set'}...")
    print(f"\n📊 Status History:")
    for change in bot.get('status_changes', [])[-5:]:
        print(f"   {change.get('created_at')} - {change.get('code')}: {change.get('message', '')}")
    
    print(f"\n🎙️ Output Media:")
    output_media = bot.get('output_media')
    if output_media:
        print(f"   Kind: {output_media.get('kind')}")
        print(f"   URL: {output_media.get('url', 'Not set')}")
        print(f"   Status: {output_media.get('status', 'unknown')}")
    else:
        print(f"   ❌ NOT CONFIGURED")
    
    print(f"\n🔗 Join At: {bot.get('join_at', 'Not set')}")
    print(f"🌐 Webhook URL: {bot.get('real_time_transcription', {}).get('destination_url', 'Not set')}")
    print(f"{'='*70}\n")
    
    # Check if bot is in meeting
    if bot.get('status_changes'):
        latest_status = bot['status_changes'][-1]['code']
        if latest_status in ['done', 'fatal', 'errored']:
            print(f"⚠️  WARNING: Bot is already {latest_status} (not in meeting)")
            print(f"   This is why Output Media never started - bot left/crashed!")
        elif latest_status in ['in_call_recording', 'in_waiting_room']:
            print(f"✅ Bot is active: {latest_status}")
        else:
            print(f"🤔 Bot status: {latest_status}")
    
    return bot

if __name__ == "__main__":
    bot_id = sys.argv[1] if len(sys.argv) > 1 else "810fa40c-ac8a-4219-a395-c32060be297f"
    check_bot(bot_id)

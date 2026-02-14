"""Temporarily disable webhook signature verification for testing"""
import os
import sys

# Update env file
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')

print("🔓 Disabling webhook signature verification...\n")

if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        lines = f.readlines()
    
    with open(env_path, 'w') as f:
        for line in lines:
            if line.startswith('RECALL_WEBHOOK_SECRET='):
                f.write(f'# {line}')  # Comment it out
                print(f"✅ Commented out: RECALL_WEBHOOK_SECRET")
            else:
                f.write(line)
    
    print("\n💡 Webhook verification is now disabled")
    print("📋 To re-enable, uncomment RECALL_WEBHOOK_SECRET in .env")
    print("\n🔄 Restart orchestrator:")
    print("   docker-compose restart orchestrator")
else:
    print("❌ .env file not found")
    sys.exit(1)

"""Test webhook connectivity and bot creation"""
import requests
import os
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

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "")
ORCHESTRATOR_URL = "http://localhost:8000"

def test_orchestrator():
    """Test if orchestrator is running"""
    print("1️⃣ Testing orchestrator connection...")
    try:
        response = requests.get(f"{ORCHESTRATOR_URL}/health", timeout=5)
        if response.status_code == 200:
            print("   ✅ Orchestrator is running")
            data = response.json()
            print(f"   📊 Queue depth: {data.get('queue_depth', 'N/A')}")
            return True
        else:
            print(f"   ❌ Orchestrator returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot connect to orchestrator: {e}")
        print(f"   💡 Run: docker-compose up -d")
        return False


def test_ngrok():
    """Test if ngrok is accessible"""
    print("\n2️⃣ Testing ngrok webhook URL...")
    
    if not PUBLIC_BASE_URL:
        print("   ❌ PUBLIC_BASE_URL is not set in .env")
        print("   💡 Set PUBLIC_BASE_URL in .env to your ngrok URL")
        return False
    
    print(f"   📡 PUBLIC_BASE_URL: {PUBLIC_BASE_URL}")
    
    # Test if ngrok URL is accessible
    try:
        webhook_url = f"{PUBLIC_BASE_URL}/health"
        response = requests.get(webhook_url, timeout=10)
        if response.status_code == 200:
            print(f"   ✅ Webhook URL is accessible")
            return True
        else:
            print(f"   ⚠️  Webhook returned: {response.status_code}")
            print(f"   💡 Check if ngrok is running: ngrok http 8000")
            return False
    except Exception as e:
        print(f"   ❌ Cannot access webhook URL: {e}")
        print(f"   💡 Make sure ngrok is running: ngrok http 8000")
        print(f"   💡 Update PUBLIC_BASE_URL in .env with your ngrok URL")
        return False


def test_webhook_endpoint():
    """Test webhook endpoint directly"""
    print("\n3️⃣ Testing webhook endpoint...")
    
    if not PUBLIC_BASE_URL:
        print("   ⏭️  Skipping (PUBLIC_BASE_URL not set)")
        return False
    
    try:
        webhook_url = f"{PUBLIC_BASE_URL}/webhooks/recall/realtime"
        # Send a test POST (will fail signature but proves endpoint exists)
        response = requests.post(
            webhook_url,
            json={"test": "data"},
            timeout=10
        )
        # 401 is expected (invalid signature), but proves endpoint exists
        if response.status_code in [401, 200]:
            print(f"   ✅ Webhook endpoint exists and is accessible")
            return True
        else:
            print(f"   ⚠️  Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Cannot access webhook endpoint: {e}")
        return False


def show_next_steps(all_passed):
    """Show next steps based on test results"""
    print("\n" + "="*70)
    if all_passed:
        print("✅ All tests passed! Ready to create bot.")
        print("\n🚀 Next steps:")
        print("   1. Stop the old bot: python scripts/stop_bot.py <bot_id>")
        print("   2. Create new bot: python scripts/create_bot.py")
        print("   3. Watch logs: python scripts/watch_logs.py")
        print("   4. Speak in meeting: 'Freya, hello!'")
    else:
        print("⚠️  Some tests failed. Fix issues above before creating bot.")
        print("\n📋 Checklist:")
        print("   □ Docker services running: docker-compose up -d")
        print("   □ ngrok running: ngrok http 8000")
        print("   □ PUBLIC_BASE_URL set in .env with ngrok URL")
        print("   □ Orchestrator restarted after .env changes")
    print("="*70)


if __name__ == "__main__":
    print("🔍 Testing Recall.ai webhook integration\n")
    print("="*70)
    
    results = []
    results.append(test_orchestrator())
    results.append(test_ngrok())
    results.append(test_webhook_endpoint())
    
    all_passed = all(results)
    show_next_steps(all_passed)
    
    sys.exit(0 if all_passed else 1)

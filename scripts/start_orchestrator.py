"""Start the bot orchestrator service locally (without Docker)"""
import sys
import os
from pathlib import Path

# Add bot-orchestrator to path
project_root = Path(__file__).parent.parent
orchestrator_path = project_root / "bot-orchestrator"
sys.path.insert(0, str(orchestrator_path))

# Change to orchestrator directory for relative imports
os.chdir(orchestrator_path)

# Load environment from src/.env
from dotenv import load_dotenv
load_dotenv(project_root / "src" / ".env")

# Set default values if not in .env
if not os.getenv("REDIS_URL"):
    os.environ["REDIS_URL"] = "redis://localhost:6379"

print("="*60)
print("🚀 Starting Bot Orchestrator Service (Local Mode)")
print("="*60)
print(f"📁 Working directory: {orchestrator_path}")
print(f"🔧 Redis URL: {os.getenv('REDIS_URL')}")
print(f"🔑 Recall API Key: {'✅ Set' if os.getenv('RECALL_API_KEY') else '❌ Not set'}")
print(f"🌐 Public URL: {os.getenv('PUBLIC_BASE_URL', 'Not set (webhooks will fail)')}")
print("="*60)
print()

# Import and run
try:
    import uvicorn
    import main
    
    print("✅ Starting FastAPI server on http://localhost:8000")
    print("   Press Ctrl+C to stop\n")
    
    uvicorn.run(main.app, host="0.0.0.0", port=8000, log_level="info")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n💡 Make sure you've installed dependencies:")
    print("   pip install -r requirements.txt")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

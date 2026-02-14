"""Start the agent worker service locally (without Docker)"""
import sys
import os
from pathlib import Path

# Add paths
project_root = Path(__file__).parent.parent
agent_worker_path = project_root / "agent-worker"
sys.path.insert(0, str(agent_worker_path))
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root / "bot-orchestrator"))

# Change to agent-worker directory for relative imports
os.chdir(agent_worker_path)

# Load environment from src/.env
from dotenv import load_dotenv
load_dotenv(project_root / "src" / ".env")

# Set default values if not in .env
if not os.getenv("REDIS_URL"):
    os.environ["REDIS_URL"] = "redis://localhost:6379"

print("="*60)
print("🚀 Starting Agent Worker Service (Local Mode)")
print("="*60)
print(f"📁 Working directory: {agent_worker_path}")
print(f"🔧 Redis URL: {os.getenv('REDIS_URL')}")
print(f"🔑 Recall API Key: {'✅ Set' if os.getenv('RECALL_API_KEY') else '❌ Not set'}")
print(f"🤖 Bot Name: {os.getenv('BOT_NAME', 'Freya')}")
print(f"🔑 FAL Key: {'✅ Set' if os.getenv('FAL_KEY') else '❌ Not set'}")
print("="*60)
print()

# Import and run
try:
    import asyncio
    import main as agent_main
    
    print("✅ Starting agent worker...")
    print("   Press Ctrl+C to stop\n")
    
    asyncio.run(agent_main.main())
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("\n💡 Make sure you've installed dependencies:")
    print("   pip install -r requirements.txt")
    import traceback
    traceback.print_exc()
    sys.exit(1)
except KeyboardInterrupt:
    print("\n\n👋 Shutting down gracefully...")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

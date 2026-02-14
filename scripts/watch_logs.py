"""Watch logs from both orchestrator and agent-worker in real-time"""
import subprocess
import sys
import os

def main():
    """Stream logs from both services"""
    print("🔍 Watching logs from orchestrator and agent-worker...")
    print("   Press Ctrl+C to stop\n")
    print("="*70)
    
    try:
        # Follow logs from both services
        process = subprocess.Popen(
            ["docker-compose", "logs", "-f", "--tail=20", "orchestrator", "agent-worker"],
            cwd=os.path.join(os.path.dirname(__file__), '..'),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Stream output
        for line in process.stdout:
            print(line, end='')
        
    except KeyboardInterrupt:
        print("\n\n👋 Stopped watching logs")
        process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()

"""
Conversational AI - Main Application
Optimized for minimal latency with streaming and parallel processing
"""
import argparse
import sys
from pathlib import Path

from config import Config
from conversation_engine import ConversationEngine
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


def print_banner():
    """Print application banner"""
    banner = Text()
    banner.append("🎤 ", style="bold blue")
    banner.append("Conversational AI ", style="bold white")
    banner.append("- Türkçe Sesli Asistan", style="bold cyan")
    
    panel = Panel(
        banner,
        border_style="blue",
        subtitle="Optimized for Low Latency"
    )
    console.print(panel)
    console.print()


def print_config_info():
    """Print configuration information"""
    console.print("[bold cyan]Configuration:[/bold cyan]")
    console.print(f"  • LLM Model: [yellow]{Config.LLM_MODEL}[/yellow]")
    console.print(f"  • Streaming TTS: [yellow]{'Enabled' if Config.ENABLE_STREAMING_TTS else 'Disabled'}[/yellow]")
    console.print(f"  • Parallel Processing: [yellow]{'Enabled' if Config.PARALLEL_PROCESSING else 'Disabled'}[/yellow]")
    console.print(f"  • Voice Activity Detection: [yellow]{'Enabled' if Config.ENABLE_VAD else 'Disabled'}[/yellow]")
    console.print()


def main():
    parser = argparse.ArgumentParser(
        description="Conversational AI with optimized latency",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Voice Activity Detection mode (hands-free)
  python main.py --vad
  
  # Manual recording mode
  python main.py --manual
  
  # Process existing audio file
  python main.py --audio user_question.wav
  
  # Fixed duration recording
  python main.py --duration 5
  
  # Change LLM model
  python main.py --vad --model anthropic/claude-3.5-sonnet
        """
    )
    
    # Recording modes
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--vad',
        action='store_true',
        help='Voice Activity Detection mode (automatic start/stop)'
    )
    group.add_argument(
        '--manual',
        action='store_true',
        help='Manual recording mode (press Enter to record)'
    )
    group.add_argument(
        '--audio',
        type=str,
        metavar='FILE',
        help='Process existing audio file'
    )
    group.add_argument(
        '--duration',
        type=float,
        metavar='SECONDS',
        help='Record for fixed duration'
    )
    
    # Configuration options
    parser.add_argument(
        '--model',
        type=str,
        help=f'LLM model to use (default: {Config.LLM_MODEL})'
    )
    parser.add_argument(
        '--no-streaming',
        action='store_true',
        help='Disable TTS streaming (may increase latency)'
    )
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing'
    )
    parser.add_argument(
        '--info',
        action='store_true',
        help='Show configuration and exit'
    )
    
    args = parser.parse_args()
    
    # Print banner
    print_banner()
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        console.print(f"[bold red]❌ Configuration Error:[/bold red] {e}")
        console.print("\n[yellow]Please check your .env file and ensure all API keys are set.[/yellow]")
        console.print("[yellow]See .env.example for required variables.[/yellow]")
        sys.exit(1)
    
    # Apply command-line overrides
    if args.model:
        Config.LLM_MODEL = args.model
    if args.no_streaming:
        Config.ENABLE_STREAMING_TTS = False
    if args.no_parallel:
        Config.PARALLEL_PROCESSING = False
    
    # Show info and exit
    if args.info:
        print_config_info()
        sys.exit(0)
    
    # Print config
    print_config_info()
    
    # Initialize conversation engine
    console.print("[bold green]✅ Initializing conversation engine...[/bold green]")
    engine = ConversationEngine()
    console.print()
    
    # Run appropriate mode
    try:
        if args.audio:
            # Process single audio file
            if not Path(args.audio).exists():
                console.print(f"[bold red]❌ Audio file not found: {args.audio}[/bold red]")
                sys.exit(1)
            
            console.print(f"[cyan]Processing audio file: {args.audio}[/cyan]\n")
            engine.single_turn(args.audio)
        
        elif args.duration:
            # Record for fixed duration
            from audio_recorder import AudioRecorder
            recorder = AudioRecorder()
            audio_file = recorder.record_fixed_duration(args.duration)
            console.print()
            engine.single_turn(audio_file)
        
        elif args.manual:
            # Manual recording mode
            engine.conversation_loop_manual()
        
        else:
            # Default to VAD mode
            if not Config.ENABLE_VAD:
                console.print("[yellow]⚠️  VAD disabled in config, using manual mode[/yellow]\n")
                engine.conversation_loop_manual()
            else:
                engine.conversation_loop_vad()
    
    except KeyboardInterrupt:
        console.print("\n\n[yellow]👋 Conversation ended by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red]❌ Error: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

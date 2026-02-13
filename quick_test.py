"""
Quick Test Script - Test conversation AI with different configurations
"""
import asyncio
import argparse
import time
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import Config
from voice_services import VoiceServices
from audio_recorder import AudioRecorder

console = Console()


class QuickTester:
    """Quick testing utility for conversation AI"""
    
    def __init__(self):
        self.services = VoiceServices()
        self.recorder = AudioRecorder()
    
    async def test_stt(self, audio_file: str = None):
        """Test Speech-to-Text"""
        console.print("\n[bold cyan]Testing STT (Speech-to-Text)...[/bold cyan]")
        
        if not audio_file:
            console.print("[yellow]Recording 5 seconds... Please speak now![/yellow]")
            audio_file = self.recorder.record_fixed_duration(5)
        
        console.print(f"[cyan]Transcribing: {audio_file}[/cyan]")
        
        start = time.time()
        text = await self.services.transcribe_audio_async(audio_file)
        latency = time.time() - start
        
        console.print(f"[green]✅ STT Result ({latency:.2f}s):[/green]")
        console.print(f"   \"{text}\"\n")
        
        return text, latency
    
    async def test_llm(self, text: str = None):
        """Test Language Model"""
        console.print("\n[bold cyan]Testing LLM (Language Model)...[/bold cyan]")
        
        if not text:
            text = "Merhaba! Nasılsın?"
        
        console.print(f"[cyan]Input: \"{text}\"[/cyan]")
        console.print(f"[cyan]Model: {Config.LLM_MODEL}[/cyan]")
        
        messages = [
            {"role": "system", "content": Config.SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]
        
        start = time.time()
        response = await self.services.generate_response_async(text, messages)
        latency = time.time() - start
        
        console.print(f"[green]✅ LLM Response ({latency:.2f}s):[/green]")
        console.print(f"   \"{response}\"\n")
        
        return response, latency
    
    async def test_tts(self, text: str = None):
        """Test Text-to-Speech"""
        console.print("\n[bold cyan]Testing TTS (Text-to-Speech)...[/bold cyan]")
        
        if not text:
            text = "Merhaba! Ben bir yapay zeka asistanıyım."
        
        console.print(f"[cyan]Input: \"{text}\"[/cyan]")
        console.print(f"[cyan]Streaming: {'Enabled' if Config.ENABLE_STREAMING_TTS else 'Disabled'}[/cyan]")
        
        start = time.time()
        
        if Config.ENABLE_STREAMING_TTS:
            # Use streaming TTS
            from audio_player import AudioPlayer
            player = AudioPlayer()
            
            console.print("[cyan]🔊 Streaming audio (playing as received)...[/cyan]")
            audio_stream = self.services.synthesize_speech_streaming_async(text)
            await player.play_streaming_async(audio_stream)
            
            latency = time.time() - start
            console.print(f"[green]✅ TTS Streaming Complete ({latency:.2f}s)[/green]\n")
            return None, latency
        else:
            # Non-streaming
            audio_data = await self.services.synthesize_speech_async(text)
            latency = time.time() - start
            
            console.print(f"[green]✅ TTS Generated ({latency:.2f}s):[/green]")
            console.print(f"   Audio size: {len(audio_data)} bytes\n")
            
            # Play audio
            console.print("[cyan]🔊 Playing audio...[/cyan]")
            from audio_player import AudioPlayer
            player = AudioPlayer()
            player.play_bytes(audio_data)
            
            return audio_data, latency
    
    async def test_full_pipeline(self, audio_file: str = None):
        """Test full pipeline (STT -> LLM -> TTS)"""
        console.print("\n[bold yellow]" + "="*60 + "[/bold yellow]")
        console.print("[bold yellow]Testing Full Pipeline (STT → LLM → TTS)[/bold yellow]")
        console.print("[bold yellow]" + "="*60 + "[/bold yellow]\n")
        
        total_start = time.time()
        
        # Step 1: STT
        user_text, stt_time = await self.test_stt(audio_file)
        
        # Step 2: LLM
        assistant_text, llm_time = await self.test_llm(user_text)
        
        # Step 3: TTS
        audio_data, tts_time = await self.test_tts(assistant_text)
        
        total_time = time.time() - total_start
        
        # Summary
        console.print("\n[bold green]" + "="*60 + "[/bold green]")
        console.print("[bold green]✅ Full Pipeline Complete![/bold green]")
        console.print("[bold green]" + "="*60 + "[/bold green]\n")
        
        table = Table(title="⏱️  Latency Summary", show_header=True)
        table.add_column("Component", style="cyan")
        table.add_column("Latency", justify="right", style="yellow")
        table.add_column("Percentage", justify="right", style="green")
        
        table.add_row("STT", f"{stt_time:.2f}s", f"{stt_time/total_time*100:.1f}%")
        table.add_row("LLM", f"{llm_time:.2f}s", f"{llm_time/total_time*100:.1f}%")
        table.add_row("TTS", f"{tts_time:.2f}s", f"{tts_time/total_time*100:.1f}%")
        table.add_row("", "", "", style="dim")
        table.add_row("TOTAL", f"{total_time:.2f}s", "100%", style="bold")
        
        console.print(table)
        console.print()
        
        # Performance assessment
        if total_time < 2.0:
            console.print("[bold green]🚀 Excellent performance! (< 2s)[/bold green]")
        elif total_time < 3.0:
            console.print("[bold yellow]✅ Good performance (2-3s)[/bold yellow]")
        elif total_time < 4.0:
            console.print("[bold yellow]⚠️  Acceptable performance (3-4s)[/bold yellow]")
        else:
            console.print("[bold red]❌ Slow performance (> 4s)[/bold red]")
            console.print("[yellow]Consider optimizations:[/yellow]")
            console.print("  • Use faster LLM model (gpt-4o-mini or gemini-flash-1.5)")
            console.print("  • Reduce LLM_MAX_TOKENS")
            console.print("  • Check network latency")
        
        console.print()
    
    async def test_config(self):
        """Test configuration and API keys"""
        console.print("\n[bold cyan]Testing Configuration...[/bold cyan]\n")
        
        errors = []
        warnings = []
        
        # Check API keys
        if not Config.FAL_KEY or Config.FAL_KEY == 'your_fal_api_key_here':
            errors.append("FAL_KEY not configured")
        else:
            console.print("[green]✅ FAL_KEY configured[/green]")
        
        # Check LLM key based on configuration
        if Config.USE_FAL_OPENROUTER:
            console.print("[green]✅ Using FAL.AI's OpenRouter (no separate key needed)[/green]")
        else:
            if not Config.OPENROUTER_KEY or Config.OPENROUTER_KEY == 'sk-or-v1-your-openrouter-key-here':
                errors.append("OPENROUTER_KEY not configured (set USE_FAL_OPENROUTER=true to use FAL's OpenRouter instead)")
            else:
                console.print("[green]✅ OPENROUTER_KEY configured[/green]")
        
        # Check settings
        console.print(f"[cyan]ℹ️  LLM Model: {Config.LLM_MODEL}[/cyan]")
        console.print(f"[cyan]ℹ️  Max Tokens: {Config.LLM_MAX_TOKENS}[/cyan]")
        console.print(f"[cyan]ℹ️  Streaming TTS: {'Enabled' if Config.ENABLE_STREAMING_TTS else 'Disabled'}[/cyan]")
        console.print(f"[cyan]ℹ️  Parallel Processing: {'Enabled' if Config.PARALLEL_PROCESSING else 'Disabled'}[/cyan]")
        console.print(f"[cyan]ℹ️  VAD: {'Enabled' if Config.ENABLE_VAD else 'Disabled'}[/cyan]")
        
        # Warnings
        if Config.LLM_MAX_TOKENS > 200:
            warnings.append(f"LLM_MAX_TOKENS is high ({Config.LLM_MAX_TOKENS}). Consider reducing to 150 for faster responses.")
        
        if not Config.ENABLE_STREAMING_TTS:
            warnings.append("Streaming TTS is disabled. Enable for lower latency.")
        
        if not Config.PARALLEL_PROCESSING:
            warnings.append("Parallel processing is disabled. Enable for better performance.")
        
        # Print results
        console.print()
        if errors:
            console.print("[bold red]❌ Configuration Errors:[/bold red]")
            for error in errors:
                console.print(f"  • {error}")
            return False
        
        if warnings:
            console.print("[bold yellow]⚠️  Configuration Warnings:[/bold yellow]")
            for warning in warnings:
                console.print(f"  • {warning}")
        
        console.print("\n[bold green]✅ Configuration is valid![/bold green]\n")
        return True
    
    async def close(self):
        """Cleanup"""
        await self.services.close()


async def main():
    parser = argparse.ArgumentParser(
        description="Quick testing utility for conversation AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test configuration only
  python quick_test.py --config
  
  # Test all components
  python quick_test.py --all
  
  # Test specific component
  python quick_test.py --stt
  python quick_test.py --llm --text "Merhaba"
  python quick_test.py --tts --text "Merhaba"
  
  # Test full pipeline
  python quick_test.py --pipeline
  python quick_test.py --pipeline --audio test.wav
        """
    )
    
    parser.add_argument('--config', action='store_true', help='Test configuration')
    parser.add_argument('--stt', action='store_true', help='Test STT')
    parser.add_argument('--llm', action='store_true', help='Test LLM')
    parser.add_argument('--tts', action='store_true', help='Test TTS')
    parser.add_argument('--pipeline', action='store_true', help='Test full pipeline')
    parser.add_argument('--all', action='store_true', help='Test all components')
    parser.add_argument('--audio', type=str, help='Audio file for testing')
    parser.add_argument('--text', type=str, help='Text for testing')
    
    args = parser.parse_args()
    
    # Banner
    panel = Panel(
        "[bold cyan]🧪 Quick Test Utility[/bold cyan]\n"
        "[white]Test conversation AI components and configuration[/white]",
        border_style="cyan"
    )
    console.print(panel)
    
    tester = QuickTester()
    
    try:
        # Default to config test if no args
        if not any([args.config, args.stt, args.llm, args.tts, args.pipeline, args.all]):
            args.config = True
        
        if args.config or args.all:
            if not await tester.test_config():
                return 1
        
        if args.all or args.pipeline:
            await tester.test_full_pipeline(args.audio)
        else:
            if args.stt:
                await tester.test_stt(args.audio)
            
            if args.llm:
                await tester.test_llm(args.text)
            
            if args.tts:
                await tester.test_tts(args.text)
        
        await tester.close()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Test interrupted by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[bold red]❌ Error:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))

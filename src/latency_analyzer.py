"""
Latency Analyzer - Measure and optimize conversation AI performance
"""
import argparse
import time
import statistics
import asyncio
from pathlib import Path
from typing import Dict, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from config import Config
from voice_services import VoiceServices

console = Console()


class LatencyAnalyzer:
    """Analyze conversation AI latency and provide optimization recommendations"""
    
    def __init__(self):
        self.services = VoiceServices()
        self.results = []
    
    async def measure_stt_latency(self, audio_file: str) -> Dict:
        """Measure STT latency"""
        start = time.time()
        text = await self.services.transcribe_audio_async(audio_file)
        latency = time.time() - start
        
        return {
            'component': 'STT',
            'latency': latency,
            'output': text[:50] + "..." if len(text) > 50 else text
        }
    
    async def measure_llm_latency(self, text: str) -> Dict:
        """Measure LLM latency"""
        messages = [
            {"role": "system", "content": Config.SYSTEM_PROMPT},
            {"role": "user", "content": text}
        ]
        
        start = time.time()
        response = await self.services.generate_response_async(text, messages)
        latency = time.time() - start
        
        return {
            'component': 'LLM',
            'latency': latency,
            'output': response[:50] + "..." if len(response) > 50 else response,
            'tokens': len(response.split())
        }
    
    async def measure_tts_latency(self, text: str) -> Dict:
        """Measure TTS latency"""
        start = time.time()
        audio_data = await self.services.synthesize_speech_async(text)
        latency = time.time() - start
        
        return {
            'component': 'TTS',
            'latency': latency,
            'output': f"{len(audio_data)} bytes"
        }
    
    async def full_pipeline_test(self, audio_file: str) -> Dict:
        """Test full pipeline (STT → LLM → TTS)"""
        console.print(f"\n[cyan]Running full pipeline test with: {audio_file}[/cyan]")
        
        total_start = time.time()
        
        # STT
        stt_result = await self.measure_stt_latency(audio_file)
        console.print(f"  ✓ STT: {stt_result['latency']:.2f}s - \"{stt_result['output']}\"")
        
        # LLM
        llm_result = await self.measure_llm_latency(stt_result['output'])
        console.print(f"  ✓ LLM: {llm_result['latency']:.2f}s - \"{llm_result['output']}\"")
        
        # TTS
        tts_result = await self.measure_tts_latency(llm_result['output'])
        console.print(f"  ✓ TTS: {tts_result['latency']:.2f}s - {tts_result['output']}")
        
        total_latency = time.time() - total_start
        
        return {
            'stt': stt_result,
            'llm': llm_result,
            'tts': tts_result,
            'total': total_latency,
            'parallel_total': max(stt_result['latency'], 0) + max(llm_result['latency'], tts_result['latency'])
        }
    
    async def run_benchmark(self, audio_file: str, iterations: int = 3) -> Dict:
        """Run multiple iterations and calculate statistics"""
        console.print(f"\n[bold yellow]🔍 Running {iterations} iterations...[/bold yellow]\n")
        
        stt_times = []
        llm_times = []
        tts_times = []
        total_times = []
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Testing...", total=iterations)
            
            for i in range(iterations):
                progress.update(task, description=f"Iteration {i+1}/{iterations}")
                result = await self.full_pipeline_test(audio_file)
                
                stt_times.append(result['stt']['latency'])
                llm_times.append(result['llm']['latency'])
                tts_times.append(result['tts']['latency'])
                total_times.append(result['total'])
                
                progress.advance(task)
                
                # Small delay between iterations
                await asyncio.sleep(0.5)
        
        return {
            'stt': {
                'mean': statistics.mean(stt_times),
                'min': min(stt_times),
                'max': max(stt_times),
                'stdev': statistics.stdev(stt_times) if len(stt_times) > 1 else 0
            },
            'llm': {
                'mean': statistics.mean(llm_times),
                'min': min(llm_times),
                'max': max(llm_times),
                'stdev': statistics.stdev(llm_times) if len(llm_times) > 1 else 0
            },
            'tts': {
                'mean': statistics.mean(tts_times),
                'min': min(tts_times),
                'max': max(tts_times),
                'stdev': statistics.stdev(tts_times) if len(tts_times) > 1 else 0
            },
            'total': {
                'mean': statistics.mean(total_times),
                'min': min(total_times),
                'max': max(total_times),
                'stdev': statistics.stdev(total_times) if len(total_times) > 1 else 0
            }
        }
    
    def print_results(self, results: Dict):
        """Print benchmark results in a nice table"""
        console.print("\n")
        
        # Create results table
        table = Table(title="📊 Latency Benchmark Results", show_header=True, header_style="bold cyan")
        table.add_column("Component", style="white", width=15)
        table.add_column("Mean", justify="right", style="yellow")
        table.add_column("Min", justify="right", style="green")
        table.add_column("Max", justify="right", style="red")
        table.add_column("StdDev", justify="right", style="blue")
        
        # Add rows
        for component in ['stt', 'llm', 'tts', 'total']:
            data = results[component]
            table.add_row(
                component.upper(),
                f"{data['mean']:.2f}s",
                f"{data['min']:.2f}s",
                f"{data['max']:.2f}s",
                f"{data['stdev']:.2f}s"
            )
        
        console.print(table)
        console.print()
    
    def print_recommendations(self, results: Dict):
        """Print optimization recommendations based on results"""
        recommendations = []
        
        # Check STT
        if results['stt']['mean'] > 1.5:
            recommendations.append("⚠️  STT is slow (>1.5s). Check audio file size and network latency.")
        
        # Check LLM
        if results['llm']['mean'] > 2.5:
            recommendations.append(f"⚠️  LLM is slow (>2.5s). Current model: {Config.LLM_MODEL}")
            recommendations.append(f"   → Try: openai/gpt-4o-mini or google/gemini-flash-1.5")
            recommendations.append(f"   → Reduce LLM_MAX_TOKENS (current: {Config.LLM_MAX_TOKENS})")
        elif results['llm']['mean'] > 1.5:
            recommendations.append(f"💡 LLM is acceptable but could be faster. Consider:")
            recommendations.append(f"   → Reduce LLM_MAX_TOKENS from {Config.LLM_MAX_TOKENS} to 100")
        
        # Check TTS
        if results['tts']['mean'] > 1.2:
            recommendations.append("⚠️  TTS is slow (>1.2s). Check network latency and response text length.")
            if not Config.ENABLE_STREAMING_TTS:
                recommendations.append("   → Enable ENABLE_STREAMING_TTS=true in .env")
        
        # Check total
        total_mean = results['total']['mean']
        if total_mean > 3.0:
            recommendations.append(f"❌ Total latency is HIGH ({total_mean:.2f}s > 3s)")
        elif total_mean > 2.0:
            recommendations.append(f"⚠️  Total latency is moderate ({total_mean:.2f}s)")
        else:
            recommendations.append(f"✅ Total latency is GOOD ({total_mean:.2f}s < 2s)")
        
        # Check parallel processing
        if not Config.PARALLEL_PROCESSING:
            recommendations.append("💡 Enable PARALLEL_PROCESSING=true for better performance")
        
        # Check consistency (standard deviation)
        if results['total']['stdev'] > 0.5:
            recommendations.append(f"⚠️  High latency variance (stdev: {results['total']['stdev']:.2f}s)")
            recommendations.append("   → This indicates network instability or API throttling")
        
        # Print recommendations
        if recommendations:
            console.print("\n[bold yellow]💡 Optimization Recommendations:[/bold yellow]\n")
            for rec in recommendations:
                console.print(f"  {rec}")
            console.print()
    
    def print_config(self):
        """Print current configuration"""
        panel = Panel(
            f"""[cyan]Current Configuration:[/cyan]
            
[white]LLM Model:[/white] [yellow]{Config.LLM_MODEL}[/yellow]
[white]Max Tokens:[/white] [yellow]{Config.LLM_MAX_TOKENS}[/yellow]
[white]Streaming TTS:[/white] [yellow]{'Enabled' if Config.ENABLE_STREAMING_TTS else 'Disabled'}[/yellow]
[white]Parallel Processing:[/white] [yellow]{'Enabled' if Config.PARALLEL_PROCESSING else 'Disabled'}[/yellow]
[white]Sample Rate:[/white] [yellow]{Config.SAMPLE_RATE} Hz[/yellow]
            """,
            title="⚙️  Configuration",
            border_style="blue"
        )
        console.print(panel)


async def main():
    parser = argparse.ArgumentParser(
        description="Analyze conversation AI latency and performance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic test with default audio
  python latency_analyzer.py
  
  # Test with custom audio file
  python latency_analyzer.py --audio user_question.wav
  
  # Run multiple iterations for statistics
  python latency_analyzer.py --iterations 5
  
  # Test only STT
  python latency_analyzer.py --component stt --audio test.wav
        """
    )
    
    parser.add_argument(
        '--audio',
        type=str,
        help='Audio file to test (default: create a test recording)'
    )
    parser.add_argument(
        '--iterations',
        type=int,
        default=3,
        help='Number of test iterations (default: 3)'
    )
    parser.add_argument(
        '--component',
        type=str,
        choices=['stt', 'llm', 'tts', 'full'],
        default='full',
        help='Component to test (default: full)'
    )
    
    args = parser.parse_args()
    
    # Banner
    console.print("\n[bold cyan]🔍 Conversation AI Latency Analyzer[/bold cyan]\n")
    
    # Validate config
    try:
        Config.validate()
    except ValueError as e:
        console.print(f"[bold red]❌ Configuration Error:[/bold red] {e}")
        return 1
    
    analyzer = LatencyAnalyzer()
    analyzer.print_config()
    
    # Check audio file
    if args.audio:
        audio_file = args.audio
        if not Path(audio_file).exists():
            console.print(f"\n[bold red]❌ Audio file not found: {audio_file}[/bold red]")
            return 1
    else:
        # Create test recording
        console.print("\n[yellow]No audio file specified. Creating a test recording...[/yellow]")
        from audio_recorder import AudioRecorder
        recorder = AudioRecorder()
        console.print("[cyan]Please speak for 3-5 seconds...[/cyan]\n")
        audio_file = recorder.record_fixed_duration(5)
        console.print(f"[green]✓ Recording saved: {audio_file}[/green]")
    
    # Run benchmark
    try:
        results = await analyzer.run_benchmark(audio_file, iterations=args.iterations)
        analyzer.print_results(results)
        analyzer.print_recommendations(results)
        
        # Summary
        console.print(f"\n[bold green]✅ Analysis complete![/bold green]")
        console.print(f"[white]Average total latency: {results['total']['mean']:.2f}s[/white]")
        console.print(f"[white]Best case: {results['total']['min']:.2f}s[/white]")
        console.print(f"[white]Worst case: {results['total']['max']:.2f}s[/white]\n")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Error during analysis:[/bold red] {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))

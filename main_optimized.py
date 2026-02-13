"""
Ultra-Optimized Conversation AI - Main Entry Point
- True real-time streaming
- In-memory audio processing
- Aggressive VAD
- Chunked LLM→TTS
"""
import asyncio
import argparse
from pathlib import Path
from audio_recorder_optimized import AudioRecorderOptimized
from conversation_engine_optimized import ConversationEngineOptimized
from config import Config

try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False


async def main():
    parser = argparse.ArgumentParser(
        description="Ultra-optimized conversational AI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('--vad', action='store_true', 
                       help='Use VAD mode (hands-free, aggressive)')
    parser.add_argument('--manual', action='store_true', 
                       help='Manual recording mode')
    parser.add_argument('--audio', type=str, 
                       help='Process audio file (.wav)')
    parser.add_argument('--duration', type=int, default=5,
                       help='Recording duration for manual mode (default: 5s)')
    parser.add_argument('--no-filler', action='store_true',
                       help='Disable filler audio')
    
    args = parser.parse_args()
    
    # Banner
    print("\n" + "="*60)
    print("🚀 ULTRA-OPTIMIZED CONVERSATIONAL AI")
    print("="*60)
    print("Optimizations:")
    print("  ✅ True PCM streaming playback")
    print("  ✅ Sentence-level TTS chunking")
    print("  ✅ In-memory audio (no disk I/O)")
    print("  ✅ Conversational VAD (ring buffer + 0.6s silence)")
    print("  ✅ Barge-in support")
    print("  ✅ Short responses (80 tokens max)")
    print("  ✅ Fast model (Gemini 2.0 Flash)")
    print("="*60 + "\n")
    
    # Initialize
    engine = ConversationEngineOptimized()
    recorder = AudioRecorderOptimized()
    
    # Determine mode
    if args.audio:
        # Process file mode
        print(f"📁 Processing audio file: {args.audio}")
        
        audio_path = Path(args.audio)
        if not audio_path.exists():
            print(f"❌ File not found: {args.audio}")
            return
        
        audio_bytes = audio_path.read_bytes()
        
        metrics = await engine.process_turn_ultra_optimized(
            audio_bytes=audio_bytes,
            use_filler=not args.no_filler
        )
        
    elif args.vad:
        # VAD mode
        if not VAD_AVAILABLE:
            print("❌ VAD not available. Install webrtcvad or use --manual mode.")
            return
        
        print("🎙️  VAD Mode - Speak naturally, system detects speech")
        print("Press Ctrl+C to exit\n")
        
        try:
            while True:
                # Record with conversational VAD (using config values)
                audio_bytes = recorder.record_to_memory_vad(
                    silence_duration=Config.SILENCE_DURATION,
                    vad_mode=Config.VAD_MODE,
                    min_speech_duration=Config.MIN_SPEECH_DURATION,
                    ring_buffer_size=Config.RING_BUFFER_SIZE
                )
                
                # Process
                metrics = await engine.process_turn_ultra_optimized(
                    audio_bytes=audio_bytes,
                    use_filler=not args.no_filler
                )
                
                print("\n" + "─"*60)
                print("Ready for next turn...")
                print("─"*60 + "\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
    
    else:
        # Manual mode (default)
        print("🎙️  Manual Mode - Press Enter to record")
        print("Press Ctrl+C to exit\n")
        
        try:
            while True:
                input("Press Enter to start recording...")
                
                # Record to memory
                audio_bytes = recorder.record_to_memory_manual(
                    duration=args.duration
                )
                
                # Process
                metrics = await engine.process_turn_ultra_optimized(
                    audio_bytes=audio_bytes,
                    use_filler=not args.no_filler
                )
                
                print("\n" + "─"*60)
                print("Ready for next turn...")
                print("─"*60 + "\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
    
    # Cleanup
    await engine.close()


if __name__ == "__main__":
    asyncio.run(main())

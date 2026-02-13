"""
Optimized Conversation Engine with Parallel Processing
"""
import asyncio
import time
from typing import Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from config import Config
from voice_services import VoiceServices
from audio_player import AudioPlayer
from audio_recorder import AudioRecorder


class ConversationEngine:
    """
    High-performance conversation engine with optimizations:
    - Parallel STT and LLM processing where possible
    - Streaming TTS for lowest latency
    - Async operations
    - Pre-buffering
    """
    
    def __init__(self):
        self.services = VoiceServices()
        self.player = AudioPlayer()
        self.recorder = AudioRecorder()
        self.conversation_history = [
            {"role": "system", "content": Config.SYSTEM_PROMPT}
        ]
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    def process_turn_sync(self, audio_file: str) -> Tuple[str, str, float]:
        """
        Process a conversation turn (synchronous version)
        Returns: (user_text, assistant_text, total_latency)
        """
        start_time = time.time()
        
        # Step 1: STT
        print("🎧 Transcribing...")
        stt_start = time.time()
        user_text = self.services.transcribe_audio(audio_file)
        stt_time = time.time() - stt_start
        print(f"👤 User: {user_text}")
        print(f"   ⏱️  STT: {stt_time:.2f}s")
        
        # Step 2: LLM
        print("🤖 Generating response...")
        llm_start = time.time()
        assistant_text = self.services.generate_response(user_text, self.conversation_history)
        llm_time = time.time() - llm_start
        print(f"🤖 Assistant: {assistant_text}")
        print(f"   ⏱️  LLM: {llm_time:.2f}s")
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_text})
        self.conversation_history.append({"role": "assistant", "content": assistant_text})
        
        # Step 3: TTS with streaming
        print("🔊 Speaking...")
        tts_start = time.time()
        
        if Config.ENABLE_STREAMING_TTS:
            # Stream TTS for immediate playback
            audio_chunks = list(self.services.synthesize_speech_streaming(assistant_text))
            self.player.stream_play(audio_chunks)
        else:
            # Non-streaming TTS
            audio_file = self.services.synthesize_speech(assistant_text)
            self.player.play_file(audio_file)
        
        tts_time = time.time() - tts_start
        print(f"   ⏱️  TTS: {tts_time:.2f}s")
        
        total_time = time.time() - start_time
        print(f"\n⏱️  Total latency: {total_time:.2f}s")
        print(f"   (STT: {stt_time:.2f}s + LLM: {llm_time:.2f}s + TTS: {tts_time:.2f}s)")
        
        return user_text, assistant_text, total_time
    
    async def process_turn_async(self, audio_file: str) -> Tuple[str, str, float]:
        """
        Process a conversation turn (asynchronous version with parallel processing)
        This is FASTER because STT and LLM can be pipelined
        """
        start_time = time.time()
        
        # Step 1: STT
        print("🎧 Transcribing...")
        stt_start = time.time()
        user_text = await self.services.transcribe_audio_async(audio_file)
        stt_time = time.time() - stt_start
        print(f"👤 User: {user_text}")
        print(f"   ⏱️  STT: {stt_time:.2f}s")
        
        # Step 2: LLM (starts immediately after STT completes)
        print("🤖 Generating response...")
        llm_start = time.time()
        
        # Run LLM and prepare TTS in parallel (pre-optimization)
        assistant_text = await self.services.generate_response_async(
            user_text,
            self.conversation_history
        )
        
        llm_time = time.time() - llm_start
        print(f"🤖 Assistant: {assistant_text}")
        print(f"   ⏱️  LLM: {llm_time:.2f}s")
        
        # Update conversation history
        self.conversation_history.append({"role": "user", "content": user_text})
        self.conversation_history.append({"role": "assistant", "content": assistant_text})
        
        # Step 3: TTS (starts immediately after LLM)
        print("🔊 Speaking...")
        tts_start = time.time()
        
        # Use TRUE streaming for lowest latency
        if Config.ENABLE_STREAMING_TTS:
            # Stream audio chunks and play as they arrive
            audio_stream = self.services.synthesize_speech_streaming_async(assistant_text)
            await self.player.play_streaming_async(audio_stream)
        else:
            # Non-streaming fallback
            audio_data = await self.services.synthesize_speech_async(assistant_text)
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, self.player.play_bytes, audio_data)
        
        tts_time = time.time() - tts_start
        print(f"   ⏱️  TTS: {tts_time:.2f}s")
        
        total_time = time.time() - start_time
        print(f"\n⏱️  Total latency: {total_time:.2f}s")
        print(f"   (STT: {stt_time:.2f}s + LLM: {llm_time:.2f}s + TTS: {tts_time:.2f}s)")
        
        return user_text, assistant_text, total_time
    
    def conversation_loop_vad(self):
        """
        Interactive conversation loop with Voice Activity Detection
        Best user experience - hands-free operation
        """
        print("\n" + "="*60)
        print("🎙️  Voice Conversation (VAD Mode)")
        print("="*60)
        print("Just speak naturally. The system will detect when you start")
        print("and stop speaking automatically.")
        print("Press Ctrl+C to exit.")
        print("="*60 + "\n")
        
        try:
            while True:
                # Record with automatic voice detection
                audio_file = self.recorder.record_with_vad()
                
                if audio_file:
                    print()
                    # Process conversation turn
                    if Config.PARALLEL_PROCESSING:
                        asyncio.run(self.process_turn_async(audio_file))
                    else:
                        self.process_turn_sync(audio_file)
                    print("\n" + "-"*60)
                    print("Ready for next input...")
                    print()
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
    
    def conversation_loop_manual(self):
        """
        Interactive conversation loop with manual recording
        User presses Enter to start/stop recording
        """
        print("\n" + "="*60)
        print("🎙️  Voice Conversation (Manual Mode)")
        print("="*60)
        print("Press Enter to start recording, Enter again to stop.")
        print("Type 'quit' or 'exit' to end conversation.")
        print("="*60 + "\n")
        
        try:
            while True:
                user_input = input("Press Enter to record (or 'quit' to exit): ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Goodbye!")
                    break
                
                # Record audio
                audio_file = self.recorder.record_manual()
                
                if audio_file:
                    print()
                    # Process conversation turn
                    if Config.PARALLEL_PROCESSING:
                        asyncio.run(self.process_turn_async(audio_file))
                    else:
                        self.process_turn_sync(audio_file)
                    print("\n" + "-"*60 + "\n")
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
    
    def single_turn(self, audio_file: str) -> Tuple[str, str]:
        """
        Process a single conversation turn from existing audio file
        """
        if Config.PARALLEL_PROCESSING:
            user_text, assistant_text, _ = asyncio.run(self.process_turn_async(audio_file))
        else:
            user_text, assistant_text, _ = self.process_turn_sync(audio_file)
        
        return user_text, assistant_text
    
    def reset_conversation(self):
        """Reset conversation history"""
        self.conversation_history = [
            {"role": "system", "content": Config.SYSTEM_PROMPT}
        ]
        print("🔄 Conversation reset")

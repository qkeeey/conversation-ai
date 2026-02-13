"""
Optimized Audio Recorder - In-Memory, Aggressive VAD
- Records directly to memory (no disk I/O)
- Aggressive VAD settings for faster cutoff
- 16kHz mono optimization
"""
import pyaudio
import wave
import struct
import time
from io import BytesIO
from pathlib import Path
from config import Config

try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    print("⚠️  webrtcvad not available. VAD mode disabled.")


class AudioRecorderOptimized:
    """Optimized audio recorder with in-memory capture"""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 channels: int = 1,
                 chunk_size: int = 480):  # 30ms at 16kHz
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.format = pyaudio.paInt16
        self.audio = pyaudio.PyAudio()
    
    def record_to_memory_vad(
        self,
        silence_threshold: int = 500,
        silence_duration: float = 0.6,  # Tuned for conversational flow
        vad_mode: int = 3,  # Aggressive VAD (0=quality, 3=aggressive)
        min_speech_duration: float = 0.3,  # Minimum speech to consider valid
        ring_buffer_size: int = 10  # Pre-roll frames (~300ms at 30ms/frame)
    ) -> bytes:
        """
        Record audio to memory with conversational VAD
        
        Features:
        - Ring buffer for pre-roll (captures start of speech)
        - Minimum speech duration (prevents false triggers)
        - Tuned silence detection (not too aggressive)
        
        Args:
            silence_threshold: RMS threshold for silence detection
            silence_duration: Seconds of silence before stopping
            vad_mode: VAD aggressiveness (0-3, 3 is most aggressive)
            min_speech_duration: Minimum speech duration to consider valid
            ring_buffer_size: Number of frames to keep in pre-roll buffer
        
        Returns:
            WAV audio bytes (in memory)
        """
        if not VAD_AVAILABLE:
            raise RuntimeError("VAD not available. Install webrtcvad.")
        
        vad = webrtcvad.Vad(vad_mode)
        
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        print("🎤 Listening... (speak now)")
        
        # Ring buffer for pre-roll (captures audio before speech detected)
        from collections import deque
        ring_buffer = deque(maxlen=ring_buffer_size)
        
        frames = []
        recording = False
        silent_chunks = 0
        speech_chunks = 0
        silence_threshold_chunks = int(silence_duration * self.sample_rate / self.chunk_size)
        min_speech_chunks = int(min_speech_duration * self.sample_rate / self.chunk_size)
        
        start_time = None
        
        try:
            while True:
                chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                
                # VAD check
                is_speech = vad.is_speech(chunk, self.sample_rate)
                
                if not recording:
                    # Before recording starts, maintain ring buffer
                    ring_buffer.append(chunk)
                    
                    if is_speech:
                        # Start recording - add ring buffer first (pre-roll)
                        recording = True
                        start_time = time.time()
                        frames.extend(list(ring_buffer))
                        speech_chunks = 1
                        silent_chunks = 0
                        print("🔴 Recording...")
                
                else:
                    # During recording
                    frames.append(chunk)
                    
                    if is_speech:
                        speech_chunks += 1
                        silent_chunks = 0
                    else:
                        silent_chunks += 1
                    
                    # Check if we should stop
                    if silent_chunks >= silence_threshold_chunks:
                        duration = time.time() - start_time
                        
                        # Verify minimum speech duration
                        if speech_chunks >= min_speech_chunks:
                            print(f"✅ Recording complete ({duration:.2f}s, {speech_chunks} speech chunks)")
                            break
                        else:
                            # Too short, false trigger - reset
                            print(f"⚠️  Too short ({speech_chunks} chunks), continuing...")
                            recording = False
                            frames = []
                            ring_buffer.clear()
        
        finally:
            stream.stop_stream()
            stream.close()
        
        # Convert frames to WAV bytes in memory
        return self._frames_to_wav_bytes(frames)
    
    def record_to_memory_manual(self, duration: int = 5) -> bytes:
        """
        Record for fixed duration to memory
        
        Args:
            duration: Recording duration in seconds
        
        Returns:
            WAV audio bytes (in memory)
        """
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.chunk_size
        )
        
        print(f"🔴 Recording for {duration} seconds...")
        
        frames = []
        num_chunks = int(self.sample_rate / self.chunk_size * duration)
        
        try:
            for _ in range(num_chunks):
                chunk = stream.read(self.chunk_size, exception_on_overflow=False)
                frames.append(chunk)
        
        finally:
            stream.stop_stream()
            stream.close()
        
        print("✅ Recording complete")
        
        return self._frames_to_wav_bytes(frames)
    
    def _frames_to_wav_bytes(self, frames: list) -> bytes:
        """
        Convert audio frames to WAV format in memory
        
        Args:
            frames: List of audio frame bytes
        
        Returns:
            Complete WAV file as bytes
        """
        wav_buffer = BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.sample_rate)
            wf.writeframes(b''.join(frames))
        
        wav_buffer.seek(0)
        return wav_buffer.read()
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'audio'):
            self.audio.terminate()

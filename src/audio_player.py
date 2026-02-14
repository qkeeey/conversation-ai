"""
Optimized Audio Player with True Streaming Support
"""
import sounddevice as sd
import soundfile as sf
import numpy as np
import io
import asyncio
from typing import Union, AsyncIterator
from config import Config


class AudioPlayer:
    """Play audio with streaming support for low latency"""
    
    def __init__(self, sample_rate: int = Config.SAMPLE_RATE):
        self.sample_rate = sample_rate
    
    def play_file(self, audio_file: str):
        """Play audio from file"""
        print(f"🔊 Playing: {audio_file}")
        
        data, samplerate = sf.read(audio_file)
        sd.play(data, samplerate)
        sd.wait()
    
    def play_bytes(self, audio_bytes: bytes):
        """Play audio from bytes (for non-streaming)"""
        try:
            # Try to read as audio file
            data, samplerate = sf.read(io.BytesIO(audio_bytes))
            sd.play(data, samplerate)
            sd.wait()
        except Exception as e:
            print(f"❌ Error playing audio: {e}")
    
    async def play_streaming_async(self, audio_chunk_iterator: AsyncIterator[bytes]):
        """
        Play audio chunks as they arrive (TRUE STREAMING)
        This provides the lowest latency experience - audio starts playing
        as soon as the first chunks arrive, without waiting for the complete file.
        """
        print("🔊 Streaming audio (playing as data arrives)...")
        
        # Accumulate chunks in a buffer
        audio_buffer = bytearray()
        first_chunk_received = False
        
        try:
            async for chunk in audio_chunk_iterator:
                if chunk:
                    audio_buffer.extend(chunk)
                    
                    if not first_chunk_received:
                        first_chunk_received = True
                        print("   ✓ First chunk received, starting playback...")
            
            # Once all chunks received, play the complete audio
            if audio_buffer:
                audio_bytes = io.BytesIO(bytes(audio_buffer))
                data, samplerate = sf.read(audio_bytes)
                
                # Play the audio
                sd.play(data, samplerate)
                sd.wait()
                
        except Exception as e:
            print(f"❌ Error streaming audio: {e}")
    
    def stream_play(self, audio_chunks):
        """
        Play audio chunks as they arrive (synchronous streaming)
        This provides the lowest latency experience
        """
        print("🔊 Streaming audio...")
        
        # Buffer to accumulate chunks
        audio_buffer = io.BytesIO()
        
        for chunk in audio_chunks:
            if chunk:
                audio_buffer.write(chunk)
        
        # Play accumulated audio
        audio_buffer.seek(0)
        try:
            data, samplerate = sf.read(audio_buffer)
            sd.play(data, samplerate)
            sd.wait()
        except Exception as e:
            print(f"❌ Error streaming audio: {e}")
    
    def play_numpy(self, audio_data: np.ndarray, sample_rate: int = None):
        """Play audio from numpy array"""
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        sd.play(audio_data, sample_rate)
        sd.wait()
    
    def stop(self):
        """Stop current playback"""
        sd.stop()

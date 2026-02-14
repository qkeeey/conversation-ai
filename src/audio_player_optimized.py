"""
Optimized Audio Player with True Real-Time PCM Streaming
- Plays PCM chunks immediately as received
- No buffering delay
- Direct PyAudio streaming
"""
import pyaudio
import struct
import asyncio
import time
from typing import AsyncIterator, Tuple
from config import Config


class AudioPlayerOptimized:
    """Ultra-low-latency audio player with real-time PCM streaming and barge-in support"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.format = pyaudio.paInt16
        self.audio = pyaudio.PyAudio()
        self.ttfa = None  # Time To First Audio
        self.current_stream = None  # Track active stream for barge-in
        self.is_playing = False  # Playback state
    
    async def play_pcm_stream_async(
        self, 
        pcm_stream: AsyncIterator[Tuple[bytes, dict]]
    ) -> dict:
        """
        Play PCM audio stream in real-time as chunks arrive
        Supports barge-in (can be stopped mid-playback)
        
        Args:
            pcm_stream: Async iterator yielding (pcm_bytes, metadata) tuples
        
        Returns:
            dict with timing metrics
        """
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            output=True,
            frames_per_buffer=1024
        )
        
        self.current_stream = stream
        self.is_playing = True
        
        start_time = time.time()
        ttfa = None  # Time To First Audio
        ttfb = None  # Time To First Byte
        chunks_played = 0
        total_bytes = 0
        
        try:
            async for pcm_bytes, metadata in pcm_stream:
                # Check if barge-in requested
                if not self.is_playing:
                    print("   ⏸️  Playback stopped (barge-in)")
                    break
                
                if metadata.get('done'):
                    # Final metadata event
                    break
                
                if pcm_bytes:
                    # Record TTFB (first byte received)
                    if ttfb is None:
                        ttfb = time.time() - start_time
                    
                    # Play chunk immediately
                    if ttfa is None:
                        ttfa = time.time() - start_time
                        print(f"   🔊 TTFA: {ttfa*1000:.0f}ms (Time To First Audio)")
                    
                    stream.write(pcm_bytes)
                    chunks_played += 1
                    total_bytes += len(pcm_bytes)
        
        except Exception as e:
            print(f"   ⚠️  Playback error: {e}")
        
        finally:
            # Wait for playback to finish
            time.sleep(0.05)
            stream.stop_stream()
            stream.close()
            self.current_stream = None
            self.is_playing = False
        
        total_time = time.time() - start_time
        
        return {
            'ttfb': ttfb,
            'ttfa': ttfa,
            'total_time': total_time,
            'chunks_played': chunks_played,
            'total_bytes': total_bytes
        }
    
    def play_pcm_bytes(self, pcm_bytes: bytes):
        """
        Play PCM audio from complete bytes
        
        Args:
            pcm_bytes: Complete PCM audio data
        """
        stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.sample_rate,
            output=True
        )
        
        try:
            stream.write(pcm_bytes)
        finally:
            stream.stop_stream()
            stream.close()
    
    def stop(self):
        """Stop all playback (barge-in)"""
        self.is_playing = False
        if self.current_stream and self.current_stream.is_active():
            try:
                self.current_stream.stop_stream()
            except:
                pass
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'audio'):
            self.audio.terminate()

"""
Optimized Audio Recorder with Voice Activity Detection
"""
import numpy as np
import sounddevice as sd
import soundfile as sf
import time
from pathlib import Path
from typing import Optional
from config import Config

# Optional: webrtcvad for Voice Activity Detection
try:
    import webrtcvad
    VAD_AVAILABLE = True
except ImportError:
    VAD_AVAILABLE = False
    print("⚠️  webrtcvad not available. VAD mode disabled. Use --manual mode instead.")


class AudioRecorder:
    """Record audio with VAD (Voice Activity Detection) for automatic start/stop"""
    
    def __init__(self, sample_rate: int = Config.SAMPLE_RATE):
        self.sample_rate = sample_rate
        if VAD_AVAILABLE:
            self.vad = webrtcvad.Vad(2)  # Aggressiveness: 0-3 (2 = balanced)
        else:
            self.vad = None
        self.is_recording = False
        self.audio_buffer = []
        
    def record_with_vad(self, output_file: Optional[str] = None) -> str:
        """
        Record audio with automatic voice activity detection.
        Starts recording when speech is detected, stops after silence.
        """
        if not VAD_AVAILABLE or self.vad is None:
            print("❌ VAD not available. Please use manual recording mode:")
            print("   python main.py --manual")
            return None
        
        print("🎙️  Listening... (speak now)")
        
        frame_duration = 30  # ms (10, 20, or 30)
        frame_size = int(self.sample_rate * frame_duration / 1000)
        
        audio_buffer = []
        silence_frames = 0
        speech_frames = 0
        max_silence_frames = int(Config.SILENCE_DURATION * 1000 / frame_duration)
        min_speech_frames = int(Config.MIN_SPEECH_DURATION * 1000 / frame_duration)
        
        recording_started = False
        
        def callback(indata, frames, time_info, status):
            nonlocal silence_frames, speech_frames, recording_started
            
            # Convert to 16-bit PCM for VAD
            audio_int16 = (indata[:, 0] * 32767).astype(np.int16)
            
            # Check if speech is detected
            try:
                is_speech = self.vad.is_speech(audio_int16.tobytes(), self.sample_rate)
            except:
                is_speech = False
            
            if is_speech:
                if not recording_started:
                    print("🎤 Speech detected, recording...")
                    recording_started = True
                
                speech_frames += 1
                silence_frames = 0
                audio_buffer.append(indata.copy())
            elif recording_started:
                silence_frames += 1
                audio_buffer.append(indata.copy())
        
        # Start streaming audio
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=Config.CHANNELS,
            callback=callback,
            blocksize=frame_size
        ):
            # Wait for speech to start
            while not recording_started:
                sd.sleep(100)
            
            # Record until silence
            while silence_frames < max_silence_frames or speech_frames < min_speech_frames:
                sd.sleep(100)
        
        print(f"✅ Recording complete ({speech_frames * frame_duration / 1000:.1f}s)")
        
        # Combine audio chunks
        if audio_buffer:
            audio_data = np.concatenate(audio_buffer, axis=0)
            
            # Save to file
            if not output_file:
                output_file = Config.OUTPUT_DIR / f"user_input_{int(time.time())}.wav"
            
            sf.write(output_file, audio_data, self.sample_rate)
            return str(output_file)
        
        return None
    
    def record_fixed_duration(self, duration: float, output_file: Optional[str] = None) -> str:
        """Record audio for a fixed duration"""
        print(f"🎙️  Recording for {duration} seconds...")
        
        audio_data = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=Config.CHANNELS,
            dtype=np.float32
        )
        sd.wait()
        
        if not output_file:
            output_file = Config.OUTPUT_DIR / f"user_input_{int(time.time())}.wav"
        
        sf.write(output_file, audio_data, self.sample_rate)
        print(f"✅ Saved: {output_file}")
        
        return str(output_file)
    
    def record_manual(self, output_file: Optional[str] = None) -> str:
        """Record until user presses Enter"""
        print("🎙️  Recording... (Press Enter to stop)")
        
        audio_buffer = []
        
        def callback(indata, frames, time_info, status):
            audio_buffer.append(indata.copy())
        
        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=Config.CHANNELS,
            callback=callback
        ):
            input()  # Wait for Enter
        
        print("✅ Recording stopped")
        
        if audio_buffer:
            audio_data = np.concatenate(audio_buffer, axis=0)
            
            if not output_file:
                output_file = Config.OUTPUT_DIR / f"user_input_{int(time.time())}.wav"
            
            sf.write(output_file, audio_data, self.sample_rate)
            return str(output_file)
        
        return None

# Ultra-Low-Latency Conversational AI - User Guide

## Quick Start

### Prerequisites
- Python 3.8+
- FAL.AI API key (required)
- Audio input/output device

### Installation

1. **Install dependencies**:
```bash
pip install aiohttp pyaudio python-dotenv
```

2. **Configure API keys** (`.env` file):
```env
FAL_KEY=your_fal_api_key_here
```

3. **Run the application**:
```bash
# With audio file
python main_optimized.py --audio data/recording01.wav

# With live microphone (voice activity detection)
python main_optimized.py
```

---

## Usage Modes

### 1. **File Mode** (Testing/Demo)
Process a pre-recorded audio file:

```bash
python main_optimized.py --audio path/to/audio.wav
```

**Input**: 
- Audio file (WAV format, 16kHz, mono preferred)
- Any audio format supported by Python's wave module

**Output**:
- Transcription printed to console
- AI response text printed to console
- AI response played through speakers
- Performance metrics (TTFA, latency breakdown)

**Example**:
```bash
python main_optimized.py --audio data/recording01.wav
```

Output:
```
============================================================
🎧 Step 1: Speech-to-Text (In-Memory)
============================================================
👤 User: Merhaba, Sultan Ahmet Camii hakkında bilgi verir misin?
   ⏱️  STT: 1308ms

============================================================
🤖 Step 2: LLM Streaming → Chunked TTS
============================================================
   🎯 First LLM token: 873ms
   🔊 Firing TTS chunk #1: "Merhaba! Sultan Ahmet Camii,..." (28 chars, speed=0.95x)
   ▶️  Playing audio chunk #1 (streaming)
   🔊 TTFA: 4254ms (Time To First Audio from start of turn)
   ...

============================================================
🤖 COMPLETE AI RESPONSE:
============================================================
Merhaba! Sultan Ahmet Camii, İstanbul'da yer alan ve 1609-1616 
yılları arasında inşa edilen bir Osmanlı camiidir...
============================================================
```

---

### 2. **Live Mode** (Interactive)
Real-time conversation with voice activity detection:

```bash
python main_optimized.py
```

**Flow**:
1. Speak into microphone
2. System detects when you stop speaking (0.6s silence)
3. AI processes and responds
4. Repeat

**Controls**:
- **Speak**: Just talk naturally
- **Stop**: Press `Ctrl+C` to exit

**Example Session**:
```
🎤 Listening... (speak naturally)
🛑 Silence detected, processing...
👤 User: Bugün hava nasıl?
🤖 AI: [Audio plays through speakers]
🤖 AI: Bugün hava güneşli ve sıcak...

🎤 Listening... (speak naturally)
```

---

## Input Requirements

### Audio Format
- **Format**: WAV (recommended) or any format Python wave module supports
- **Sample Rate**: 16kHz (optimal), but system auto-converts
- **Channels**: Mono (recommended), stereo will be converted
- **Bit Depth**: 16-bit PCM

### Speech Requirements
- **Language**: Turkish (system is optimized for Turkish)
- **Duration**: 0.3s - 30s recommended
- **Quality**: Clear speech, minimal background noise

---

## Output Format

### Console Output

#### 1. **Real-Time Progress**
```
🎧 Step 1: Speech-to-Text (In-Memory)
👤 User: [Your transcribed speech]
   ⏱️  STT: 1308ms

🤖 Step 2: LLM Streaming → Chunked TTS
   🎯 First LLM token: 873ms
   🔊 Firing TTS chunk #1: "..." (28 chars, speed=0.95x)
   ▶️  Playing audio chunk #1 (streaming)
   🔊 TTFA: 4254ms (Time To First Audio from start of turn)
   ✅ Finished playing chunk #1
```

#### 2. **Complete Response**
```
============================================================
🤖 COMPLETE AI RESPONSE:
============================================================
[Full AI response text]
============================================================
```

#### 3. **Performance Metrics**
```
============================================================
📊 PERFORMANCE METRICS
============================================================

🎧 STT:
   Latency: 1308ms

🤖 LLM:
   First Token: 873ms
   Total: 6046ms
   Chunks: 130

🔊 TTS:
   TTS Calls: 11
   Call 1: TTFB: 1235ms | TTFA: 0ms | Total: 0ms

⏱️  TOTAL:
   TTFA (Time To First Audio): 4254ms
   End-to-End: 7511ms

📊 TTFA Breakdown:
   1. STT (transcription): 1308ms
   2. LLM (first token): 873ms
   3. TTS generation + playback: 2073ms
   ─────────────────────────────
   Total TTFA: 4254ms

🚀 EXCELLENT! TTFA < 1.5s
============================================================
```

### Audio Output
- AI response played through **default audio output device**
- **Format**: 16-bit PCM, 16kHz, mono
- **Playback**: Streaming (starts as soon as first chunk ready)
- **Speed**: Variable (0.95x - 1.15x with progressive ramping)

---

## Configuration

### Basic Configuration (`.env`)

```env
# API Keys (Required)
FAL_KEY=your_fal_api_key_here

# LLM Settings
LLM_PROVIDER=fal              # Options: fal, openrouter, gemini
LLM_MODEL=google/gemini-2.0-flash-exp:free
LLM_TEMPERATURE=0.7           # 0.0=deterministic, 1.0=creative
LLM_MAX_TOKENS=300            # Response length limit

# TTS Settings
TTS_SPEED=1.15                # Playback speed (1.0=normal)
TTS_CHUNK_MIN_CHARS=20        # Minimum chunk size
TTS_CHUNK_MAX_CHARS=100       # Maximum chunk size

# Progressive Speed Ramping
TTS_SPEED_INITIAL=0.95        # Start slower (prevent stuttering)
TTS_SPEED_RAMP_CHUNKS=3       # Ramp over 3 chunks
ENABLE_SPEED_RAMPING=true     # Enable/disable ramping

# Audio Settings
AUDIO_SAMPLE_RATE=16000       # 16kHz for voice
AUDIO_CHANNELS=1              # Mono
SILENCE_THRESHOLD=500         # Silence detection threshold
SILENCE_DURATION=0.6          # Silence duration to stop recording
```

### Advanced Configuration

#### LLM Provider Selection

**Option 1: FAL.AI (Default)**
```env
LLM_PROVIDER=fal
FAL_KEY=your_fal_api_key_here
```

**Option 2: Direct OpenRouter**
```env
LLM_PROVIDER=openrouter
OPENROUTER_KEY=sk-or-v1-your-key-here
```

**Option 3: Direct Google Gemini**
```env
LLM_PROVIDER=gemini
GEMINI_KEY=your_gemini_api_key_here
LLM_MODEL=gemini-2.0-flash-exp  # No prefix for direct Gemini
```

#### Performance Tuning

**Faster Response (Lower Quality)**
```env
TTS_CHUNK_MIN_CHARS=15        # Fire TTS earlier
TTS_CHUNK_MAX_CHARS=80        # Smaller chunks
TTS_SPEED=1.25                # Faster playback
LLM_MAX_TOKENS=150            # Shorter responses
```

**Better Quality (Slower)**
```env
TTS_CHUNK_MIN_CHARS=30        # Wait for more context
TTS_CHUNK_MAX_CHARS=150       # Larger chunks
TTS_SPEED=1.0                 # Normal playback
LLM_MAX_TOKENS=500            # Longer responses
ENABLE_SPEED_RAMPING=false    # Disable ramping
```

**Turkish-Optimized (Recommended)**
```env
TTS_CHUNK_MIN_CHARS=20
TTS_CHUNK_MAX_CHARS=100
TTS_SPEED=1.15
TTS_SPEED_INITIAL=0.95
ENABLE_SPEED_RAMPING=true
```

---

## Understanding Performance Metrics

### TTFA (Time To First Audio)
**What it is**: Time from when you stop speaking until you hear the first audio response.

**Ideal Values**:
- 🚀 **<1.5s**: Excellent (feels instant)
- ✅ **1.5-2.0s**: Good (natural conversation)
- ⚠️ **2.0-2.5s**: Acceptable (slight delay)
- ❌ **>2.5s**: Slow (noticeable lag)

### TTFA Breakdown

```
📊 TTFA Breakdown:
   1. STT (transcription): 1308ms     ← Speech-to-text conversion
   2. LLM (first token): 873ms        ← AI thinking time
   3. TTS generation + playback: 2073ms ← Audio synthesis + start playing
   ─────────────────────────────
   Total TTFA: 4254ms
```

**How to optimize**:
- **STT**: Use faster internet, clearer speech
- **LLM**: Choose faster model, shorter prompts
- **TTS**: Enable speed ramping, smaller chunks

---

## Troubleshooting

### Problem: "No audio output"
**Solution**: 
1. Check system audio settings
2. Verify audio device is not muted
3. Test with `python -c "import pyaudio; p = pyaudio.PyAudio(); print(p.get_default_output_device_info())"`

### Problem: "High TTFA (>3 seconds)"
**Solution**:
1. Check internet connection speed
2. Reduce `TTS_CHUNK_MAX_CHARS` to 80
3. Reduce `LLM_MAX_TOKENS` to 200
4. Enable `ENABLE_SPEED_RAMPING=true`

### Problem: "Audio stuttering"
**Solution**:
1. Enable speed ramping: `ENABLE_SPEED_RAMPING=true`
2. Lower initial speed: `TTS_SPEED_INITIAL=0.9`
3. Increase ramp chunks: `TTS_SPEED_RAMP_CHUNKS=4`
4. Check CPU usage (close other apps)

### Problem: "API errors"
**Solution**:
1. Verify FAL_KEY is correct in `.env`
2. Check FAL.AI account status
3. Test API: `curl -H "Authorization: Key YOUR_KEY" https://fal.run/status`

### Problem: "Silence not detected (live mode)"
**Solution**:
1. Increase `SILENCE_DURATION` to 1.0
2. Adjust `SILENCE_THRESHOLD` (higher = less sensitive)
3. Speak clearly and pause at end

---

## Example Commands

### Basic Usage
```bash
# Process single audio file
python main_optimized.py --audio recording.wav

# Live conversation
python main_optimized.py

# With custom config
FAL_KEY=your_key python main_optimized.py --audio test.wav
```

### Testing
```bash
# Test with sample audio
python main_optimized.py --audio data/recording01.wav

# Test streaming fix
python test_streaming_fix.py

# Test true streaming with monitoring
python test_true_streaming.py
```

---

## Tips for Best Experience

### 1. **Clear Speech**
- Speak naturally, not too fast or slow
- Pause 0.5-1s at end of question
- Minimize background noise

### 2. **Optimal Questions**
- Short questions (5-15 seconds)
- Clear pronunciation
- One question at a time

### 3. **Performance**
- Use fast internet (5+ Mbps)
- Close other apps (reduce CPU load)
- Use wired headphones (lower latency than Bluetooth)

### 4. **Configuration**
- Start with defaults
- Tune only if experiencing issues
- Test changes with same audio file

---

## File Structure

```
conversation/
├── main_optimized.py              # Entry point
├── conversation_engine_optimized.py  # Core orchestration
├── voice_services_optimized.py    # STT/LLM/TTS APIs
├── audio_player_optimized.py      # Audio playback
├── audio_recorder_optimized.py    # Audio recording
├── config.py                      # Configuration
├── .env                           # API keys & settings
├── data/                          # Sample audio files
│   └── recording01.wav
└── outputs/                       # Generated files (if any)
```

---

## API Key Setup

### Getting FAL.AI API Key
1. Sign up at https://fal.ai
2. Go to Dashboard → API Keys
3. Generate new key
4. Copy to `.env` file:
   ```env
   FAL_KEY=your_key_here
   ```

### Optional: OpenRouter API Key
1. Sign up at https://openrouter.ai
2. Go to Keys → Generate
3. Copy to `.env`:
   ```env
   OPENROUTER_KEY=sk-or-v1-your_key_here
   LLM_PROVIDER=openrouter
   ```

### Optional: Google Gemini API Key
1. Sign up at https://makersuite.google.com
2. Get API key
3. Copy to `.env`:
   ```env
   GEMINI_KEY=your_gemini_key_here
   LLM_PROVIDER=gemini
   ```

---

## Support

### Common Issues
- See **Troubleshooting** section above
- Check logs for error messages
- Verify API keys are valid

### Performance Tuning
- See **Advanced Configuration** section
- Adjust chunk sizes for your use case
- Test with different models

### Documentation
- `TECHNICAL_ARCHITECTURE.md` - Detailed implementation
- `GAPLESS_STREAMING_FIX.md` - Streaming optimization details
- Code comments - Inline documentation

---

**Last Updated**: February 14, 2026  
**Version**: 2.0 (Gapless Streaming)

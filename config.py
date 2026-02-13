"""
Configuration for Conversational AI
"""
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    """Application configuration"""
    
    # API Keys
    FAL_KEY = os.getenv('FAL_KEY')
    OPENROUTER_KEY = os.getenv('OPENROUTER_KEY')  # Optional: not needed if using FAL's OpenRouter
    GEMINI_KEY = os.getenv('GEMINI_KEY')  # For direct Google Gemini API
    
    # LLM Provider Selection (choose one)
    # Options: 'fal' (FAL.AI OpenRouter), 'openrouter' (Direct), 'gemini' (Direct Google)
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'fal').lower()
    
    # Legacy support
    USE_FAL_OPENROUTER = os.getenv('USE_FAL_OPENROUTER', 'true').lower() == 'true'
    if not USE_FAL_OPENROUTER and LLM_PROVIDER == 'fal':
        LLM_PROVIDER = 'openrouter'
    
    # Endpoints
    TTS_ENDPOINT = os.getenv('TTS_ENDPOINT', 'freya-mypsdi253hbk/freya-tts')
    STT_ENDPOINT = os.getenv('STT_ENDPOINT', 'freya-mypsdi253hbk/freya-stt')
    LLM_ENDPOINT = os.getenv('LLM_ENDPOINT', 'openrouter/router')
    
    # Full URLs
    TTS_SPEECH_URL = f"https://fal.run/{TTS_ENDPOINT}/audio/speech"
    TTS_STREAM_URL = f"https://fal.run/{TTS_ENDPOINT}/stream"
    STT_TRANSCRIPTIONS_URL = f"https://fal.run/{STT_ENDPOINT}/audio/transcriptions"
    
    # Base URLs for streaming
    TTS_BASE_URL = f"https://fal.run/{TTS_ENDPOINT}"
    
    # LLM Configuration based on provider
    if LLM_PROVIDER == 'gemini':
        LLM_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
        LLM_URL = f"{LLM_BASE_URL}/models"
    elif LLM_PROVIDER == 'openrouter':
        LLM_BASE_URL = "https://openrouter.ai/api/v1"
        LLM_URL = f"{LLM_BASE_URL}/chat/completions"
    else:  # 'fal' (default)
        LLM_BASE_URL = f"https://fal.run/{LLM_ENDPOINT}"
        LLM_URL = f"https://fal.run/{LLM_ENDPOINT}"
    
    # Audio Settings
    SAMPLE_RATE = int(os.getenv('AUDIO_SAMPLE_RATE', '16000'))
    CHANNELS = int(os.getenv('AUDIO_CHANNELS', '1'))
    CHUNK_SIZE = 1024
    AUDIO_FORMAT = 'mp3'
    
    # Voice Activity Detection (Tuned for conversational flow)
    SILENCE_THRESHOLD = int(os.getenv('SILENCE_THRESHOLD', '500'))
    SILENCE_DURATION = float(os.getenv('SILENCE_DURATION', '0.6'))  # Faster but not too aggressive
    MIN_SPEECH_DURATION = float(os.getenv('MIN_SPEECH_DURATION', '0.3'))  # Minimum valid speech
    RING_BUFFER_SIZE = int(os.getenv('RING_BUFFER_SIZE', '10'))  # Pre-roll frames (~300ms)
    VAD_MODE = int(os.getenv('VAD_MODE', '3'))  # Aggressive mode
    
    # LLM Settings (Optimized for low latency with natural conversation)
    # Model name format depends on provider:
    # - fal: 'google/gemini-2.0-flash-exp:free'
    # - openrouter: 'google/gemini-2.0-flash-exp:free'
    # - gemini: 'gemini-2.0-flash-exp' (no prefix)
    _default_model = 'google/gemini-2.0-flash-exp:free' if LLM_PROVIDER != 'gemini' else 'gemini-2.0-flash-exp'
    LLM_MODEL = os.getenv('LLM_MODEL', _default_model)
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.7'))  # Natural conversation
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', '300'))  # Reasonable limit, not restrictive
    
    # System Prompt (Natural conversational assistant)
    SYSTEM_PROMPT = """Sen Freya, Türkçe sesli asistan.
Doğal ve samimi bir şekilde konuş. Kısa ve net cevaplar ver, ama gerekirse detay ekle.
Kullanıcının sorusunu tam olarak yanıtla."""
    
    # Performance Settings
    ENABLE_STREAMING_TTS = os.getenv('ENABLE_STREAMING_TTS', 'true').lower() == 'true'
    
    # TTS Chunking Settings (ULTRA-AGGRESSIVE for lowest latency)
    TTS_CHUNK_MIN_CHARS = int(os.getenv('TTS_CHUNK_MIN_CHARS', '20'))  # Very low minimum
    TTS_CHUNK_MAX_CHARS = int(os.getenv('TTS_CHUNK_MAX_CHARS', '100'))  # Force fire earlier
    TTS_SPEED = float(os.getenv('TTS_SPEED', '1.15'))  # Faster playback (still natural)
    
    # Progressive Speed Ramping (prevents stuttering in early chunks)
    # Start slower to give TTS time to build buffer, then speed up
    TTS_SPEED_INITIAL = float(os.getenv('TTS_SPEED_INITIAL', '0.95'))  # Slower for first chunks
    TTS_SPEED_RAMP_CHUNKS = int(os.getenv('TTS_SPEED_RAMP_CHUNKS', '3'))  # Ramp over N chunks
    ENABLE_SPEED_RAMPING = os.getenv('ENABLE_SPEED_RAMPING', 'true').lower() == 'true'
    
    # Check if webrtcvad is available
    try:
        import webrtcvad
        _VAD_AVAILABLE = True
    except ImportError:
        _VAD_AVAILABLE = False
    
    # Only enable VAD if module is available
    ENABLE_VAD = os.getenv('ENABLE_VAD', 'true').lower() == 'true' and _VAD_AVAILABLE
    PARALLEL_PROCESSING = os.getenv('PARALLEL_PROCESSING', 'true').lower() == 'true'
    
    # Timeouts
    STT_TIMEOUT = 10
    LLM_TIMEOUT = 15
    TTS_TIMEOUT = 10
    
    # Output
    OUTPUT_DIR = Path(__file__).parent / "outputs"
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    @classmethod
    def validate(cls):
        """Validate configuration"""
        errors = []
        
        # Check LLM provider-specific keys
        if cls.LLM_PROVIDER == 'gemini':
            if not cls.GEMINI_KEY or cls.GEMINI_KEY == 'your_gemini_api_key_here':
                errors.append("GEMINI_KEY not configured (required when LLM_PROVIDER=gemini)")
        elif cls.LLM_PROVIDER == 'openrouter':
            if not cls.OPENROUTER_KEY or cls.OPENROUTER_KEY == 'sk-or-v1-your-openrouter-key-here':
                errors.append("OPENROUTER_KEY not configured (required when LLM_PROVIDER=openrouter)")
        else:  # 'fal'
            if not cls.FAL_KEY or cls.FAL_KEY == 'your_fal_api_key_here':
                errors.append("FAL_KEY not configured (required when LLM_PROVIDER=fal)")
        
        # STT/TTS always need FAL_KEY (for now)
        if not cls.FAL_KEY or cls.FAL_KEY == 'your_fal_api_key_here':
            errors.append("FAL_KEY not configured (required for STT/TTS)")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True

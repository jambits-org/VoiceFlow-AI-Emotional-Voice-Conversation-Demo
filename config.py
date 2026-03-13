import os
import secrets
from dotenv import load_dotenv

load_dotenv()

# App
APP_TITLE = os.getenv("APP_TITLE", "VoiceFlow AI")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OTP_CODE = os.getenv("OTP_CODE", "8472")
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "10"))
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))

# Models
STT_MODEL = os.getenv("STT_MODEL", "whisper-1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
TTS_MODEL = os.getenv("TTS_MODEL", "tts-1-hd")

# Voice
TTS_VOICE = os.getenv("TTS_VOICE", "nova")
TTS_SPEED = float(os.getenv("TTS_SPEED", "0.95"))

# LLM tuning
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "150"))
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.9"))
LLM_PRESENCE_PENALTY = float(os.getenv("LLM_PRESENCE_PENALTY", "0.6"))
LLM_FREQUENCY_PENALTY = float(os.getenv("LLM_FREQUENCY_PENALTY", "0.3"))
LLM_HISTORY_LIMIT = int(os.getenv("LLM_HISTORY_LIMIT", "6"))

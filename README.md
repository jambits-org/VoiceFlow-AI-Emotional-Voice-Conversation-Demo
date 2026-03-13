# VoiceFlow AI — Emotional Voice Conversation Demo

A lightweight proof-of-concept for ultra-realistic AI voice conversations. Built to demonstrate how LLMs, speech-to-text, and expressive TTS can be combined into a seamless, emotionally aware voice experience.

**This is a working demo** — not a mockup. Deploy it, share the link and an access code with your client, and let the voice do the talking.

## What It Does

User speaks → Whisper transcribes → GPT generates an emotionally shaped response → TTS converts it to natural speech with pauses, warmth, and tone variation → audio plays back.

The focus is on making the AI *feel* human: filler words, thoughtful pauses, emotional mirroring, varied sentence rhythm. Not robotic. Not scripted.

## Stack

- **Backend:** Python / FastAPI
- **AI:** OpenAI (Whisper + GPT-4o-mini + TTS)
- **Storage:** SQLite (sessions, message history, OTP tracking)
- **Frontend:** Vanilla JS + Tailwind CSS (single-page, no framework)

## Quick Start

```bash
git clone https://github.com/jambits-org/VoiceFlow-AI-Emotional-Voice-Conversation-Demo.git
cd VoiceFlow-AI-Emotional-Voice-Conversation-Demo
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

Create `.env`:
```
OPENAI_API_KEY=sk-your-key
OTP_CODE=8472
MAX_ATTEMPTS=10
```

Run:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000`, enter the access code, tap the mic.

## How Access Control Works

Each OTP code is single-use. Once verified, it's burned — refreshing or re-entering the same code won't work. The session gets a fixed number of voice interactions (default 10). Change the code in `.env` and restart to issue a new one.

## Project Structure

```
├── main.py           # App entry point + DB init
├── config.py         # Environment config
├── routes.py         # API endpoints
├── prompts.py        # LLM system prompt (voice shaping)
├── db.py             # SQLite persistence layer
├── static/
│   ├── app.js        # Recording, playback, UI logic
│   └── styles.css    # Animations + glassmorphism
└── templates/
    └── index.html    # Single-page UI
```

## License

MIT

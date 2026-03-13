import io
import base64
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from openai import OpenAI

from config import (
    OPENAI_API_KEY, MAX_ATTEMPTS,
    STT_MODEL, LLM_MODEL, TTS_MODEL, TTS_VOICE, TTS_SPEED,
    LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_PRESENCE_PENALTY,
    LLM_FREQUENCY_PENALTY, LLM_HISTORY_LIMIT,
)
from prompts import SYSTEM_PROMPT
from db import (
    verify_and_claim_otp, get_session, decrement_attempts,
    refund_attempt, add_message, get_history,
)

router = APIRouter()
client = OpenAI(api_key=OPENAI_API_KEY)
TEMPLATES_DIR = Path(__file__).parent / "templates"


def _get_session_id(request: Request) -> str:
    sid = request.session.get("session_id")
    if not sid:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sid


@router.get("/", response_class=HTMLResponse)
async def index():
    html = (TEMPLATES_DIR / "index.html").read_text()
    return HTMLResponse(html)


@router.post("/api/verify-otp")
async def verify_otp(request: Request, otp: str = Form(...)):
    session_id = verify_and_claim_otp(otp.strip())
    if not session_id:
        raise HTTPException(status_code=401, detail="Invalid or already used access code")
    request.session["session_id"] = session_id
    return {"attempts_left": MAX_ATTEMPTS}


@router.get("/api/session-status")
async def session_status(request: Request):
    sid = request.session.get("session_id")
    if not sid:
        return JSONResponse({"active": False})
    session = get_session(sid)
    if not session:
        request.session.clear()
        return JSONResponse({"active": False})
    history = get_history(sid, limit=50)
    return JSONResponse({
        "active": True,
        "attempts_left": session["attempts_left"],
        "history": history,
    })


@router.post("/api/chat")
async def chat(request: Request, audio: UploadFile = File(...)):
    session_id = _get_session_id(request)
    session = get_session(session_id)
    if not session:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Invalid session")
    if session["attempts_left"] <= 0:
        raise HTTPException(status_code=429, detail="No attempts remaining")

    decrement_attempts(session_id)

    try:
        # 1. Transcribe with Whisper
        audio_bytes = await audio.read()
        transcript = client.audio.transcriptions.create(
            model=STT_MODEL,
            file=("audio.webm", io.BytesIO(audio_bytes), "audio/webm"),
        )
        user_text = transcript.text
        add_message(session_id, "user", user_text)

        # 2. Build context from DB history
        history = get_history(session_id, limit=LLM_HISTORY_LIMIT)
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

        completion = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            max_tokens=LLM_MAX_TOKENS,
            temperature=LLM_TEMPERATURE,
            presence_penalty=LLM_PRESENCE_PENALTY,
            frequency_penalty=LLM_FREQUENCY_PENALTY,
        )
        reply_text = completion.choices[0].message.content
        add_message(session_id, "assistant", reply_text)

        # 3. TTS
        speech = client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=reply_text,
            speed=TTS_SPEED,
        )
        audio_b64 = base64.b64encode(speech.content).decode("utf-8")

        updated = get_session(session_id)
        return JSONResponse({
            "user_text": user_text,
            "reply_text": reply_text,
            "audio": audio_b64,
            "attempts_left": updated["attempts_left"],
        })

    except Exception as e:
        refund_attempt(session_id)
        raise HTTPException(status_code=500, detail=str(e))

import io
import base64
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from openai import OpenAI

from config import (
    OPENAI_API_KEY,
    STT_MODEL, LLM_MODEL, TTS_MODEL, TTS_VOICE, TTS_SPEED,
    LLM_MAX_TOKENS, LLM_TEMPERATURE, LLM_PRESENCE_PENALTY,
    LLM_FREQUENCY_PENALTY, LLM_HISTORY_LIMIT,
)
from prompts import SYSTEM_PROMPT
from db import verify_otp, get_status, decrement_attempts, refund_attempt, add_message, get_history

router = APIRouter()
client = OpenAI(api_key=OPENAI_API_KEY)
TEMPLATES_DIR = Path(__file__).parent / "templates"


@router.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse((TEMPLATES_DIR / "index.html").read_text())


@router.post("/api/verify-otp")
async def api_verify_otp(otp: str = Form(...)):
    result = verify_otp(otp.strip())
    if not result:
        raise HTTPException(status_code=401, detail="Invalid access code")
    if result["attempts_left"] <= 0:
        raise HTTPException(status_code=429, detail="No attempts remaining for this code")
    return {"code": result["code"], "attempts_left": result["attempts_left"]}


@router.post("/api/session-status")
async def session_status(code: str = Form(...)):
    result = get_status(code.strip())
    if not result:
        return JSONResponse({"active": False})
    history = get_history(code.strip(), limit=50)
    return JSONResponse({
        "active": True,
        "attempts_left": result["attempts_left"],
        "history": history,
    })


@router.post("/api/chat")
async def chat(code: str = Form(...), audio: UploadFile = File(...)):
    result = get_status(code.strip())
    if not result:
        raise HTTPException(status_code=401, detail="Invalid access code")
    if result["attempts_left"] <= 0:
        raise HTTPException(status_code=429, detail="No attempts remaining")

    decrement_attempts(code.strip())

    try:
        audio_bytes = await audio.read()
        transcript = client.audio.transcriptions.create(
            model=STT_MODEL,
            file=("audio.webm", io.BytesIO(audio_bytes), "audio/webm"),
        )
        user_text = transcript.text
        add_message(code.strip(), "user", user_text)

        history = get_history(code.strip(), limit=LLM_HISTORY_LIMIT)
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
        add_message(code.strip(), "assistant", reply_text)

        speech = client.audio.speech.create(
            model=TTS_MODEL,
            voice=TTS_VOICE,
            input=reply_text,
            speed=TTS_SPEED,
        )
        audio_b64 = base64.b64encode(speech.content).decode("utf-8")

        updated = get_status(code.strip())
        return JSONResponse({
            "user_text": user_text,
            "reply_text": reply_text,
            "audio": audio_b64,
            "attempts_left": updated["attempts_left"],
        })

    except Exception as e:
        refund_attempt(code.strip())
        raise HTTPException(status_code=500, detail=str(e))

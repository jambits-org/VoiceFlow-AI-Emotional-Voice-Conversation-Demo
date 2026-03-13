from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from config import APP_TITLE, OTP_CODE, SESSION_SECRET
from db import init_db, seed_otp
from routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_otp(OTP_CODE)
    yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    max_age=86400,
    session_cookie="voiceflow_session",
    same_site="lax",
    https_only=False,
    path="/",
)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)

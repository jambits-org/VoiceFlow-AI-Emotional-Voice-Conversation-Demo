from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config import APP_TITLE, OTP_CODE
from db import init_db, seed_otp
from routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_otp(OTP_CODE)
    yield


app = FastAPI(title=APP_TITLE, lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)

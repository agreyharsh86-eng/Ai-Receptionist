"""Main FastAPI Application for AI Corporate Receptionist."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from pathlib import Path

from app.database import init_db
from app.database_mongo import init_mongo, close_mongo, is_mongo_connected
from app.api.routes import router as api_router
from app.api.auth_routes import router as auth_router
from app.api.websocket import router as ws_router
import app.config as config

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite legacy tables if needed & MongoDB unified store
    await init_db()
    await init_mongo()
    print("=" * 60)
    print(f"[*] {config.COMPANY_NAME} AI Receptionist System Initialized")
    print(f"[*] Receptionist Persona: {config.RECEPTIONIST_NAME}")
    print(f"[*] Gemini API Key configured: {bool(config.GEMINI_API_KEY)}")
    print(f"[*] Live Model: {config.GEMINI_LIVE_MODEL}")
    print(f"[*] MongoDB DB: {config.MONGODB_DB_NAME} (connected={is_mongo_connected()})")
    print(f"[*] Server running at: http://{config.HOST}:{config.PORT}")
    print("=" * 60)
    yield
    await close_mongo()

app = FastAPI(
    title="Corporate AI Receptionist",
    description="Real-time Voice AI Front Desk & Virtual Receptionist powered by Gemini Live API",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routers
app.include_router(api_router)
app.include_router(auth_router)
app.include_router(ws_router)

# Mount Static UI & Jinja2 Templates
STATIC_DIR = config.BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

TEMPLATES_DIR = config.BASE_DIR / "templates"
TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index(request: Request):
    index_template = TEMPLATES_DIR / "index.html"
    if index_template.exists():
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "company_name": config.COMPANY_NAME,
                "company_industry": config.COMPANY_INDUSTRY,
                "receptionist_name": config.RECEPTIONIST_NAME,
                "live_model": config.GEMINI_LIVE_MODEL,
                "default_voice": config.DEFAULT_VOICE
            }
        )
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "AI Receptionist Backend Active."}

"""Main FastAPI Application for AI Corporate Receptionist."""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.database import init_db
from app.api.routes import router as api_router
from app.api.websocket import router as ws_router
import app.config as config

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize SQLite tables and seed data
    await init_db()
    print("=" * 60)
    print(f"[*] {config.COMPANY_NAME} AI Receptionist System Initialized")
    print(f"[*] Receptionist Persona: {config.RECEPTIONIST_NAME}")
    print(f"[*] Gemini API Key configured: {bool(config.GEMINI_API_KEY)}")
    print(f"[*] Live Model: {config.GEMINI_LIVE_MODEL}")
    print(f"[*] Server running at: http://{config.HOST}:{config.PORT}")
    print("=" * 60)
    yield
    # Shutdown logic if any

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
app.include_router(ws_router)

# Mount Static UI
STATIC_DIR = config.BASE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def serve_index():
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": f"AI Receptionist Backend Active. Static frontend not yet compiled."}

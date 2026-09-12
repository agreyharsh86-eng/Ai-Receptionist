"""Launcher script for AI Corporate Receptionist Application."""

import os
import sys
import uvicorn
from pathlib import Path

# Ensure UTF-8 output on Windows terminals
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass

BASE_DIR = Path(__file__).resolve().parent

if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  [*] APEX HORIZON ENTERPRISES -- AI VOICE RECEPTIONIST")
    print("=" * 65)
    print("  Front Desk Web Console: http://127.0.0.1:8000")
    print("  API Documentation:      http://127.0.0.1:8000/docs")
    print("=" * 65 + "\n")

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        log_level="info"
    )

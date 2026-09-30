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
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    reload = os.getenv("RELOAD", "true").lower() in ("true", "1", "yes")

    display_host = "127.0.0.1" if host == "0.0.0.0" else host
    print("\n" + "=" * 65)
    print("  [*] APEX HORIZON ENTERPRISES -- AI VOICE RECEPTIONIST")
    print("=" * 65)
    print(f"  Front Desk Web Console: http://{display_host}:{port}")
    print(f"  API Documentation:      http://{display_host}:{port}/docs")
    print("=" * 65 + "\n")

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )

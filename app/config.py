import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "receptionist.db"

# Load .env file
load_dotenv(BASE_DIR / ".env")

# Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_LIVE_MODEL = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.1-flash-live-preview")
GEMINI_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")
DEFAULT_VOICE = os.getenv("DEFAULT_VOICE", "Aoede")  # Options: Aoede, Puck, Charon, Fenrir, Kore

HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

# Receptionist Persona Configuration
RECEPTIONIST_NAME = "Aria"
COMPANY_NAME = "Apex Horizon Enterprises"
COMPANY_INDUSTRY = "Enterprise Cloud & AI Solutions"
COMPANY_LOCATION = "Tower 4, Suite 1200, 500 Silicon Vista Way, Innovation District"
COMPANY_HOURS = "Monday to Friday: 8:30 AM – 5:30 PM EST. Saturday & Sunday: Closed."

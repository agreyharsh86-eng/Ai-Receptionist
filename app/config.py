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

def is_valid_gemini_key(key: str) -> bool:
    """Validate whether an API key is a genuine Gemini API key and not a placeholder."""
    if not key:
        return False
    k = key.strip().lower()
    if k.startswith("your_") or k.startswith("placeholder") or "api_key_here" in k or len(k) < 15:
        return False
    return True

def has_valid_api_key() -> bool:
    """Check if a valid Gemini API key is configured."""
    return is_valid_gemini_key(GEMINI_API_KEY)

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

# Receptionist Persona Configuration
RECEPTIONIST_NAME = "Jack"
COMPANY_NAME = "HR Enterprises"
COMPANY_INDUSTRY = "Enterprise Cloud, AI Solutions & Healthcare Consultation"
COMPANY_LOCATION = "Tower 4, Suite 1200, 500 Silicon Vista Way, Innovation District"
COMPANY_HOURS = "Monday to Friday: 8:30 AM – 5:30 PM EST. Saturday & Sunday: Closed."

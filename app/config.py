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

# Application Environment
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
MONGO_STRICT = os.getenv("MONGO_STRICT", "false").strip().lower() in ("true", "1", "yes") or APP_ENV == "production"

# MongoDB Database Configuration
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://127.0.0.1:27017")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "jack_receptionist")
MONGO_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv("MONGO_SERVER_SELECTION_TIMEOUT_MS", "5000"))
MONGO_CONNECT_TIMEOUT_MS = int(os.getenv("MONGO_CONNECT_TIMEOUT_MS", "5000"))
MONGO_SOCKET_TIMEOUT_MS = int(os.getenv("MONGO_SOCKET_TIMEOUT_MS", "10000"))
MONGO_MAX_POOL_SIZE = int(os.getenv("MONGO_MAX_POOL_SIZE", "50"))
MONGO_MIN_POOL_SIZE = int(os.getenv("MONGO_MIN_POOL_SIZE", "5"))

# Authentication & JWT Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "jack-ai-receptionist-secret-key-2026-auth-token")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080")) # 7 days
OTP_EXPIRE_SECONDS = int(os.getenv("OTP_EXPIRE_SECONDS", "30")) # 30 seconds expiry as required
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))

# Resend Email Delivery Configuration
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "JACK <onboarding@resend.dev>")

# SMS Delivery Configuration (Twilio)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

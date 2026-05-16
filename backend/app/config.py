from pydantic_settings import BaseSettings
from typing import List, Optional, Any
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Try to load local.env first, then .env
# Search in current dir, then parent dir (project root)
def get_env_path(filename):
    if os.path.exists(filename):
        return filename
    parent_path = os.path.join("..", filename)
    if os.path.exists(parent_path):
        return parent_path
    return None

env_path = get_env_path("local.env") or get_env_path(".env")
if env_path:
    load_dotenv(env_path)
    logger.info(f"Loaded configuration from {env_path}")
else:
    print("No configuration file (local.env or .env) found! Using system environment variables.")

# Log raw os.environ values BEFORE Settings is instantiated so we can confirm
# what the Python process actually sees at startup (values are masked for security).
def _mask(val: str) -> str:
    if not val:
        return "MISSING/EMPTY"
    if len(val) <= 8:
        return "****"
    return f"{val[:4]}...{val[-4:]}"

_raw_groq = os.environ.get("GROQ_API_KEY", "")
_raw_sarvam = os.environ.get("SARVAM_API_KEY", "")
print(f"[config] PRE-INIT os.environ GROQ_API_KEY  : {_mask(_raw_groq)}")
print(f"[config] PRE-INIT os.environ SARVAM_API_KEY: {_mask(_raw_sarvam)}")

# Try to import Groq, gracefully degrade if not available
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None
    logger.warning("groq package not installed. Groq features will be unavailable.")

class Settings(BaseSettings):
    # API Keys — NO os.getenv() defaults here.
    # pydantic-settings reads directly from os.environ, so using os.getenv() as
    # a default value would freeze the value at class-definition time (before
    # Railway injects env vars) and prevent pydantic from ever overriding it.
    groq_api_key: str = ""
    gemini_api_key: str = ""
    sarvam_api_key: str = ""

    # Auth Settings
    admin_username: str = "admin"
    admin_password: str = "admin"
    secret_key: str = "supersecretkey"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Direct Groq client initialization
    groq_client: Optional[Any] = None

    # Gemini settings
    gemini_model: str = "gemini-2.0-flash"
    gemini_temperature: float = 0.3
    gemini_max_tokens: int = 500

    # Directories
    chroma_persist_dir: str = "chroma_db"
    upload_dir: str = "uploads"
    temp_audio_dir: str = "temp_audio"

    # CORS settings
    cors_origins: str = "*"  # Comma-separated or *

    # College information
    college_name: str = "Dr. B.C. Roy Engineering College"
    admissions_phone: str = "0343-2501353"
    support_email: str = "info@bcrec.ac.in"

    class Config:
        env_file = ".env"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Log what pydantic-settings resolved after reading os.environ / env_file
        logger.info(f"[Settings] GROQ_API_KEY  resolved: {_mask(self.groq_api_key)}")
        logger.info(f"[Settings] SARVAM_API_KEY resolved: {_mask(self.sarvam_api_key)}")

        # Validate required keys and raise early with a clear message if missing
        missing = []
        if not self.groq_api_key:
            missing.append("GROQ_API_KEY")
        if not self.sarvam_api_key:
            missing.append("SARVAM_API_KEY")
        if missing:
            msg = (
                f"Required environment variable(s) not set: {', '.join(missing)}. "
                "Please configure them in Railway (or your .env file for local development)."
            )
            logger.error(f"[Settings] {msg}")
            raise ValueError(msg)

        # Initialize Groq client
        if GROQ_AVAILABLE:
            try:
                self.groq_client = Groq(api_key=self.groq_api_key)
                logger.info("[Settings] Groq client initialized successfully")
            except Exception as e:
                logger.error(f"[Settings] Failed to initialize Groq client: {e}")
                self.groq_client = None
        else:
            logger.error("[Settings] Groq library NOT installed — Groq features unavailable")
            self.groq_client = None

# Create settings instance
settings = Settings()

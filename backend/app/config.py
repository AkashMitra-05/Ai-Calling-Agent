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
    # Check if required keys are already in environment (e.g., Railway)
    groq_key_present = bool(os.getenv("GROQ_API_KEY"))
    sarvam_key_present = bool(os.getenv("SARVAM_API_KEY"))
    if groq_key_present and sarvam_key_present:
        logger.info("No .env file found — using Railway/system environment variables (GROQ_API_KEY and SARVAM_API_KEY detected).")
    else:
        missing = [k for k, v in {"GROQ_API_KEY": groq_key_present, "SARVAM_API_KEY": sarvam_key_present}.items() if not v]
        logger.warning(
            f"No configuration file (local.env or .env) found and the following required environment "
            f"variables are missing: {', '.join(missing)}. Using system environment variables."
        )

# Debug: log raw env values at module load time so Railway logs show what the process sees
_raw_groq_key = os.getenv("GROQ_API_KEY", "")
_raw_sarvam_key = os.getenv("SARVAM_API_KEY", "")
logger.info(
    f"[config] Environment variable check — "
    f"GROQ_API_KEY: {'SET (length={})'.format(len(_raw_groq_key)) if _raw_groq_key else 'NOT SET or EMPTY'}, "
    f"SARVAM_API_KEY: {'SET (length={})'.format(len(_raw_sarvam_key)) if _raw_sarvam_key else 'NOT SET or EMPTY'}"
)

# Try to import Groq, gracefully degrade if not available
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    Groq = None
    logger.warning("groq package not installed. Groq features will be unavailable.")

class Settings(BaseSettings):
    # API Keys
    groq_api_key: str = os.getenv("GROQ_API_KEY", "")
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    sarvam_api_key: str = os.getenv("SARVAM_API_KEY", "")

    # Auth Settings
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "admin")
    secret_key: str = os.getenv("SECRET_KEY", "supersecretkey")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # Direct Groq client initialization
    groq_client: Optional[Any] = None
    
    # Gemini settings
    gemini_model: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    gemini_temperature: float = float(os.getenv("GEMINI_TEMPERATURE", "0.3"))
    gemini_max_tokens: int = int(os.getenv("GEMINI_MAX_TOKENS", "500"))
    
    # Directories
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "chroma_db")
    upload_dir: str = os.getenv("UPLOAD_DIR", "uploads")
    temp_audio_dir: str = os.getenv("TEMP_AUDIO_DIR", "temp_audio")
    
    # CORS settings
    cors_origins: str = "*"  # Comma-separated or *
    
    # College information
    college_name: str = os.getenv("COLLEGE_NAME", "Dr. B.C. Roy Engineering College")
    admissions_phone: str = os.getenv("ADMISSIONS_PHONE", "0343-2501353")
    support_email: str = os.getenv("SUPPORT_EMAIL", "info@bcrec.ac.in")
    
    class Config:
        env_file = ".env"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Debug: confirm what pydantic-settings resolved for each key after field population
        logger.info(
            f"[Settings.__init__] Resolved field values — "
            f"groq_api_key: {'SET (length={})'.format(len(self.groq_api_key)) if self.groq_api_key else 'EMPTY — GROQ_API_KEY not received by pydantic-settings'}, "
            f"sarvam_api_key: {'SET (length={})'.format(len(self.sarvam_api_key)) if self.sarvam_api_key else 'EMPTY — SARVAM_API_KEY not received by pydantic-settings'}"
        )

        # Validate required API keys and raise early with a clear message if missing
        if not self.groq_api_key:
            logger.error(
                "[Settings.__init__] GROQ_API_KEY is missing or empty. "
                "Set the GROQ_API_KEY environment variable in Railway (or your .env file) and redeploy."
            )
            raise ValueError(
                "Required environment variable GROQ_API_KEY is not set. "
                "Add it to your Railway service variables and redeploy."
            )

        if not self.sarvam_api_key:
            logger.error(
                "[Settings.__init__] SARVAM_API_KEY is missing or empty. "
                "Set the SARVAM_API_KEY environment variable in Railway (or your .env file) and redeploy."
            )
            raise ValueError(
                "Required environment variable SARVAM_API_KEY is not set. "
                "Add it to your Railway service variables and redeploy."
            )

        # Initialize Groq client
        if not GROQ_AVAILABLE:
            logger.error("[Settings.__init__] groq package is not installed — cannot initialize Groq client.")
            self.groq_client = None
        else:
            try:
                self.groq_client = Groq(api_key=self.groq_api_key)
                logger.info("[Settings.__init__] Groq client initialized successfully.")
            except Exception as e:
                logger.error(f"[Settings.__init__] Failed to initialize Groq client: {e}")
                self.groq_client = None

# Create settings instance
settings = Settings()

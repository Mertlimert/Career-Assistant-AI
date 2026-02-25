"""Configuration for Career Assistant AI Agent."""
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

_PROJECT_ROOT = Path(__file__).resolve().parent
_ENV_FILE = _PROJECT_ROOT / ".env"

if _ENV_FILE.exists():
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_FILE, override=True)
    except Exception:
        pass


class Settings(BaseSettings):
    """Application settings from environment."""
    gemini_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    evaluation_threshold: int = 70
    max_revision_attempts: int = 3

    model_config = {
        "env_file": _ENV_FILE if _ENV_FILE.exists() else None,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()

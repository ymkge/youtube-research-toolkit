import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
default_db_path = os.path.join(backend_dir, "youtube_research.db")

class Settings(BaseSettings):
    PROJECT_NAME: str = "YouTube Research Toolkit"
    DATABASE_URL: str = f"sqlite:///{default_db_path}"
    
    # API Keys
    YOUTUBE_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-flash-latest"
    GEMINI_FALLBACK_MODEL: str = "gemini-flash-lite-latest"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

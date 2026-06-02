from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    flask_secret_key: str
    flask_debug: bool = False
    redis_url: str = "redis://redis:6379/0"
    max_file_size_mb: int = 100
    max_requests_per_minute: int = 10
    whisperx_service_url: str = "http://whisperx:5001"
    database_url: str = "sqlite:///./db/karaoke_songs.db"
    ngrok_auth_token: str | None = None
    huggingface_token: str | None = None
    log_level: str = "INFO"
    storage_backend: Literal["local", "r2"] = "local"
    r2_account_id: str | None = None
    r2_bucket: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    # Magic-link email (Resend). Optional so dev boots without it; production must set it.
    resend_api_key: str | None = None
    resend_from_email: str = "KaraokeIA <onboarding@resend.dev>"
    app_base_url: str = "http://localhost:8000"

    model_config = {"env_file": ".env", "case_sensitive": False}

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        import logging

        if not hasattr(logging, v.upper()):
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()

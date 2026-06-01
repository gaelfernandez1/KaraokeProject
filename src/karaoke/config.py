from typing import Optional
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
    ngrok_auth_token: Optional[str] = None
    huggingface_token: Optional[str] = None
    log_level: str = "INFO"

    model_config = {"env_file": ".env", "case_sensitive": False}

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        import logging
        if not hasattr(logging, v.upper()):
            raise ValueError(f"Invalid log level: {v}")
        return v.upper()

"""Configuration de l'application."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from einstein_core import __version__


class Settings(BaseSettings):
    """Configuration chargée depuis les variables d'environnement."""

    model_config = SettingsConfigDict(
        env_prefix="EINSTEIN_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Einstein Core"
    environment: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    version: str = __version__
    ai_enabled: bool = False
    ai_provider: Literal["openai", "chatgpt"] = "openai"
    ai_model: str | None = Field(default=None, min_length=1, pattern=r"\S")
    ai_api_key_file: Path | None = None
    ai_chatgpt_credentials_file: Path | None = None
    ai_max_output_chars: int = Field(default=8192, ge=1, le=65536)
    ai_timeout_seconds: float = Field(default=20, gt=0, le=120, allow_inf_nan=False)
    ai_max_output_tokens: int = Field(default=512, ge=1, le=4096)
    ai_max_concurrency: int = Field(default=1, ge=1, le=8)
    ai_max_context_bytes: int = Field(default=32768, ge=1, le=262144)
    maison_inventory_path: Path = Path("config/equipements.example.json")


@lru_cache
def get_settings() -> Settings:
    """Retourne la configuration mise en cache."""

    return Settings()

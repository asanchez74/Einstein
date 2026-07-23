"""Configuration de l'application."""

from functools import lru_cache
from typing import Literal

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


@lru_cache
def get_settings() -> Settings:
    """Retourne la configuration mise en cache."""

    return Settings()

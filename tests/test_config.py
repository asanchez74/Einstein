"""Tests de la configuration."""

from einstein_core.config import Settings


def test_default_settings() -> None:
    settings = Settings()

    assert settings.app_name == "Einstein Core"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"


def test_settings_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("EINSTEIN_ENVIRONMENT", "test")
    monkeypatch.setenv("EINSTEIN_LOG_LEVEL", "DEBUG")

    settings = Settings()

    assert settings.environment == "test"
    assert settings.log_level == "DEBUG"

"""Tests de la configuration."""

import pytest
from pydantic import ValidationError

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


@pytest.mark.parametrize(
    ("variable", "value", "field"),
    [
        ("EINSTEIN_ENVIRONMENT", "staging", "environment"),
        ("EINSTEIN_LOG_LEVEL", "TRACE", "log_level"),
    ],
)
def test_invalid_settings_from_environment(monkeypatch, variable, value, field) -> None:
    monkeypatch.setenv(variable, value)

    with pytest.raises(ValidationError) as exc_info:
        Settings()

    assert any(
        error["loc"] == (field,) and error["type"] == "literal_error"
        for error in exc_info.value.errors()
    )

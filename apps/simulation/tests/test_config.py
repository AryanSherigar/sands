import pytest
from app.config import (
    DEFAULT_SECRET_KEY,
    DEFAULT_SIMULATION_DATABASE_URL,
    DEFAULT_SIMULATION_TEST_DATABASE_URL,
    Settings,
)
from pydantic import ValidationError


def test_defaults() -> None:
    settings = Settings()
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.simulation_database_url == DEFAULT_SIMULATION_DATABASE_URL
    assert settings.simulation_test_database_url == DEFAULT_SIMULATION_TEST_DATABASE_URL
    assert settings.simulation_db_pool_min_size == 1
    assert settings.simulation_db_pool_max_size == 10
    assert settings.simulation_db_pool_timeout_seconds == 30


def test_explicit_value_overrides_default() -> None:
    assert Settings(simulation_db_pool_max_size=3).simulation_db_pool_max_size == 3


def test_unknown_environment_variable_is_ignored(monkeypatch) -> None:
    monkeypatch.setenv("SOMETHING_UNRELATED", "1")
    assert Settings().environment == "development"


def test_auth_defaults() -> None:
    settings = Settings()
    assert settings.secret_key == DEFAULT_SECRET_KEY
    assert settings.jwt_algorithm == "HS256"
    assert settings.internal_service_token == ""


@pytest.mark.parametrize("secret_key", [DEFAULT_SECRET_KEY, "short"])
def test_production_refuses_default_or_short_secret(secret_key: str) -> None:
    with pytest.raises(ValidationError):
        Settings(environment="production", secret_key=secret_key)


def test_production_accepts_a_long_secret() -> None:
    assert (
        Settings(environment="production", secret_key="x" * 32).environment
        == "production"
    )


def test_development_accepts_the_default_secret() -> None:
    assert Settings(environment="development").secret_key == DEFAULT_SECRET_KEY


def test_intent_provider_is_off_by_default_and_hard_bounded() -> None:
    settings = Settings()
    assert settings.intent_provider_enabled is False
    assert settings.intent_provider_timeout_seconds == 2
    assert settings.intent_provider_max_output_tokens == 256
    with pytest.raises(ValidationError):
        Settings(intent_provider_timeout_seconds=2.01)
    with pytest.raises(ValidationError):
        Settings(intent_provider_max_output_tokens=257)

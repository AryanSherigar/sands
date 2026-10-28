"""Simulation service configuration module. The only place environment variables are read."""

from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SIMULATION_DATABASE_URL = (
    "postgresql://simulation_db:simulation_db@localhost:5434/simulation_db"
)
DEFAULT_SIMULATION_TEST_DATABASE_URL = (
    "postgresql://simulation_db:simulation_db@127.0.0.1:5434/simulation_test_db"
)
DEFAULT_DB_POOL_MIN_SIZE = 1
DEFAULT_DB_POOL_MAX_SIZE = 10
DEFAULT_DB_POOL_TIMEOUT_SECONDS = 30.0
DEFAULT_SECRET_KEY = "default-secret-key-change-in-production"
MIN_PRODUCTION_SECRET_KEY_LENGTH = 32
DEFAULT_JWT_ALGORITHM = "HS256"
WORLD_SEED_UPPER_BOUND = 2**63
DEFAULT_INTENT_TIMEOUT_SECONDS = 2.0
DEFAULT_INTENT_WORKER_POLL_SECONDS = 0.25
DEFAULT_INTENT_PROVIDER_MAX_TOKENS = 256
DEFAULT_SPEECH_TIMEOUT_SECONDS = 8.0
DEFAULT_SPEECH_PROVIDER_MAX_TOKENS = 128
DEFAULT_STANCE_TIMEOUT_SECONDS = 8.0
DEFAULT_STANCE_PROVIDER_MAX_TOKENS = 128
DEFAULT_STANCE_WORKER_POLL_SECONDS = 0.5


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    log_level: str = "INFO"
    simulation_database_url: str = DEFAULT_SIMULATION_DATABASE_URL
    simulation_test_database_url: str = DEFAULT_SIMULATION_TEST_DATABASE_URL
    simulation_db_pool_min_size: int = DEFAULT_DB_POOL_MIN_SIZE
    simulation_db_pool_max_size: int = DEFAULT_DB_POOL_MAX_SIZE
    simulation_db_pool_timeout_seconds: float = DEFAULT_DB_POOL_TIMEOUT_SECONDS
    secret_key: str = DEFAULT_SECRET_KEY
    jwt_algorithm: str = DEFAULT_JWT_ALGORITHM
    internal_service_token: str = ""
    summary_lease_seconds: int = Field(default=120, ge=90, le=600)
    summary_max_attempts: int = Field(default=3, ge=1, le=10)
    intent_provider_enabled: bool = False
    intent_provider_url: str = ""
    intent_provider_api_key: str = ""
    intent_provider_model: str = ""
    intent_provider_timeout_seconds: float = Field(
        default=DEFAULT_INTENT_TIMEOUT_SECONDS, gt=0, le=DEFAULT_INTENT_TIMEOUT_SECONDS
    )
    intent_worker_poll_seconds: float = Field(
        default=DEFAULT_INTENT_WORKER_POLL_SECONDS, gt=0, le=5
    )
    intent_provider_max_output_tokens: int = Field(
        default=DEFAULT_INTENT_PROVIDER_MAX_TOKENS,
        ge=1,
        le=DEFAULT_INTENT_PROVIDER_MAX_TOKENS,
    )
    speech_provider_enabled: bool = False
    speech_provider_url: str = ""
    speech_provider_api_key: str = ""
    speech_provider_model: str = ""
    speech_provider_timeout_seconds: float = Field(
        default=DEFAULT_SPEECH_TIMEOUT_SECONDS,
        gt=0,
        le=DEFAULT_SPEECH_TIMEOUT_SECONDS,
    )
    speech_provider_max_output_tokens: int = Field(
        default=DEFAULT_SPEECH_PROVIDER_MAX_TOKENS,
        ge=1,
        le=DEFAULT_SPEECH_PROVIDER_MAX_TOKENS,
    )

    stance_provider_enabled: bool = False
    stance_provider_url: str = ""
    stance_provider_api_key: str = ""
    stance_provider_model: str = ""
    stance_provider_timeout_seconds: float = Field(
        default=DEFAULT_STANCE_TIMEOUT_SECONDS,
        gt=0,
        le=DEFAULT_STANCE_TIMEOUT_SECONDS,
    )
    stance_provider_max_output_tokens: int = Field(
        default=DEFAULT_STANCE_PROVIDER_MAX_TOKENS,
        ge=1,
        le=DEFAULT_STANCE_PROVIDER_MAX_TOKENS,
    )
    stance_worker_poll_seconds: float = Field(
        default=DEFAULT_STANCE_WORKER_POLL_SECONDS, gt=0, le=5
    )

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Refuse to boot in production with the default or a weak secret_key."""
        if self.environment == "production" and (
            self.secret_key == DEFAULT_SECRET_KEY
            or len(self.secret_key) < MIN_PRODUCTION_SECRET_KEY_LENGTH
        ):
            raise ValueError(
                "FATAL: Insecure SECRET_KEY configured in production environment!"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

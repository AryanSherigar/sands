"""Core API Configuration module."""

import uuid

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "default-secret-key-change-in-production"
MIN_PRODUCTION_SECRET_KEY_LENGTH = 32


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/sands_db"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    secret_key: str = DEFAULT_SECRET_KEY
    admin_database_url: str = ""
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 15
    jwt_refresh_expire_days: int = 7
    refresh_rotation_grace_seconds: int = 30
    share_token_expire_days: int = 30
    scenario_invite_ttl_days: int = 7
    firebase_project_id: str = "ai-dnd-47eb0"
    firebase_credentials_path: str = ""
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]
    environment: str = "development"
    frontend_base_url: str = "http://localhost:5173"
    log_level: str = "INFO"
    log_format: str = "json"
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_public_base_url: str = ""
    r2_endpoint_url: str = ""
    r2_region: str = "auto"
    r2_request_timeout_seconds: float = 30.0
    core_api_public_url: str = "http://localhost:8000"
    local_upload_dir: str = "uploads"
    gemini_api_key: str = ""
    image_generation_model_name: str = "gemini-3.1-flash-image"
    image_generation_timeout_seconds: int = 30
    lyria_model_name: str = "lyria-002"
    simulation_url: str = "http://localhost:8081"
    simulation_internal_token: str = ""
    simulation_initialize_timeout_seconds: float = 15.0
    memory_url: str = "http://localhost:8080"
    memory_service_name: str = "core-api"
    is_memory_iam_auth_enabled: bool = False
    # NOTE: The direct write runs inside the request with no model calls; it is
    # measured at a few seconds for novel-scale lore, so 60s leaves headroom
    # for a cold-started memory instance.
    memory_template_timeout_seconds: int = 60
    memory_purge_timeout_seconds: int = 10
    memory_purge_max_consecutive_failures: int = 3
    memory_outbox_retention_days: int = 7
    memory_reconcile_min_age_hours: int = 24
    account_deletion_grace_days: int = 30
    account_purge_batch_size: int = 50
    account_purge_user_limit: int = 100
    deleted_user_id: uuid.UUID = uuid.UUID("00000000-0000-0000-0000-00000000dead")
    stats_range_days: dict[str, int] = {"7d": 7, "30d": 30, "90d": 90}
    stats_daily_bucket_max_days: int = 30
    stats_min_sample_playthroughs: int = 5
    stats_min_benchmark_peers: int = 5
    stats_repeat_player_min_playthroughs: int = 2
    # NOTE: The last threshold mirrors TRS play_count_increment_turn_threshold
    # so "reached turn 10" lines up with the public play_count.
    stats_funnel_turn_thresholds: list[int] = [3, 10]
    stats_turn_distribution_edges: list[int] = [1, 3, 5, 10, 20, 50]
    stats_rating_scale: list[int] = [1, 2, 3, 4, 5]
    stats_latest_reviews_limit: int = 10
    stats_overview_reviews_limit: int = 5
    stats_listed_statuses: list[str] = ["published", "archived"]

    is_alpha_mode: bool = False
    alpha_scenario_id: uuid.UUID | None = None
    is_alpha_signup_enabled: bool = True
    alpha_consent_version: str = "alpha-1"
    alpha_public_url: str = ""
    alpha_tension_prompt_every_turns: int = 15
    alpha_event_max_batch: int = 50
    alpha_event_max_body_bytes: int = 32 * 1024
    alpha_health_window_hours: int = 24
    alpha_stale_run_hours: int = 24
    alpha_max_turns_without_metrics_ratio: float = 0.01
    alpha_max_memory_degraded_rate: float = 0.20
    alpha_min_completion_rate: float = 0.0
    alpha_daily_budget_usd: float = 0.0
    alpha_spend_alert_fraction: float = 0.8
    alpha_prompt_usd_per_million_tokens: float = 0.0
    alpha_completion_usd_per_million_tokens: float = 0.0

    is_rate_limit_enabled: bool = True
    # NOTE: Count of proxies appending to X-Forwarded-For in front of this
    # service; the client is that many entries from the right. Locally nginx
    # is the only hop (1); on Cloud Run the Google front end adds one (2).
    trusted_proxy_hops: int = 0
    internal_proxy_token: str = ""
    rate_limit_exempt_firebase_uids: str = ""
    rate_limit_exempt_cache_seconds: int = 300
    rate_limit_cleanup_interval_seconds: int = 600
    rate_limit_window_seconds: int = 60
    rate_limit_auth_per_window: int = 10
    rate_limit_logs_per_window: int = 30
    rate_limit_alpha_events_per_window: int = 30
    rate_limit_ai_generation_per_window: int = 10
    rate_limit_upload_per_window: int = 20
    rate_limit_write_per_window: int = 60
    rate_limit_read_per_window: int = 120
    rate_limit_anonymous_per_window: int = 60
    rate_limit_ip_ceiling_per_window: int = 600
    quota_cover_image_per_user: int = 10
    quota_cover_image_global: int = 150
    quota_music_generation_per_user: int = 10
    quota_music_generation_global: int = 60
    quota_publish_per_user: int = 10
    quota_publish_global: int = 100
    new_accounts_per_ip_per_day: int = 3
    client_log_max_body_bytes: int = 64 * 1024
    client_log_max_message_length: int = 2000

    @property
    def exempt_firebase_uids(self) -> frozenset[str]:
        return frozenset(
            uid.strip()
            for uid in self.rate_limit_exempt_firebase_uids.split(",")
            if uid.strip()
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

    @property
    def is_r2_configured(self) -> bool:
        return all(
            (
                self.r2_access_key_id,
                self.r2_secret_access_key,
                self.r2_bucket_name,
                self.r2_public_base_url,
                self.r2_endpoint,
            )
        )

    @property
    def r2_endpoint(self) -> str:
        if self.r2_endpoint_url:
            return self.r2_endpoint_url.rstrip("/")
        if not self.r2_account_id:
            return ""
        return f"https://{self.r2_account_id}.r2.cloudflarestorage.com"

    @model_validator(mode="after")
    def validate_production_storage(self) -> "Settings":
        """Refuse to boot in production without object storage, instead of
        silently writing uploads to local disk."""
        if self.environment == "production" and not self.is_r2_configured:
            raise ValueError(
                "FATAL: R2 object storage must be configured in production "
                "(R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, "
                "R2_BUCKET_NAME, R2_PUBLIC_BASE_URL)"
            )
        return self

    @model_validator(mode="after")
    def validate_alpha_scenario(self) -> "Settings":
        """Refuse to boot in alpha mode without the playable scenario id."""
        if self.is_alpha_mode and self.alpha_scenario_id is None:
            raise ValueError(
                "FATAL: ALPHA_SCENARIO_ID is required when IS_ALPHA_MODE is on"
            )
        return self


settings = Settings()

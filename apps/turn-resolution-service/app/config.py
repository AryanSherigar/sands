"""Turn Resolution Service Configuration module."""

from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

WELCOME_SAMPLE_RATE = 44100
WELCOME_MAX_AUDIO_SECONDS = 12
WELCOME_PCM_SCALE = 32768
WELCOME_VOICE_RMS = 0.105
WELCOME_HIGH_PASS_HZ = 100
WELCOME_LOW_PASS_HZ = 4200
WELCOME_FILTER_ORDER = 8
WELCOME_ACTIVE_THRESHOLD = 0.01
WELCOME_TAPE_DRIVE = 1.18
WELCOME_WOW_SAMPLES = 6
WELCOME_WOW_HZ = 0.65
WELCOME_PEAK_LIMIT = 0.87
WELCOME_TAPE_ID = "tallis-v1"
WELCOME_NAME_MAX_LENGTH = 60
WELCOME_NAME_PUNCTUATION = " '-\u2019"

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
    jwt_algorithm: str = "HS256"
    cors_origins: list[str] = ["http://localhost:5173"]
    environment: str = "development"

    gemini_api_key: str = ""
    is_vertex_adc_enabled: bool = False
    google_cloud_project: str = ""
    google_cloud_location: str = "global"
    narration_max_output_tokens_ceiling: int = 4096
    narration_timeout_seconds: int = 30
    narration_max_retries: int = 2
    openai_compatible_open_retries: int = 1
    openai_compatible_open_retry_delay_seconds: float = 0.5
    narration_provider: Literal["openai", "anthropic"] = "openai"
    anthropic_model_name: str = "claude-haiku-5-5"
    anthropic_max_output_tokens: int = 1024
    anthropic_effort: str = "low"
    openai_compatible_base_url: str = "https://api.meta.ai/v1"
    openai_compatible_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("openai_compatible_api_key", "muse_api_key"),
    )
    openai_compatible_model_name: str = "muse-spark-1.3"
    openai_compatible_reasoning_effort: str = "minimal"
    recent_window_turns: int = 5
    repetition_window_turns: int = 3
    repetition_phrase_limit: int = 8
    turn_action_max_chars: int = 2000
    turn_action_hard_max_chars: int = 20000
    state_block_tokens: int = 800
    facts_block_tokens: int = 800
    active_card_cap: int = 6
    active_card_tokens: int = 1200
    lore_fallback_tokens: int = 1500
    prompt_chars_per_token: int = 3
    play_count_increment_turn_threshold: int = 10
    state_write_max_retries: int = 2
    memory_retrieval_enabled: bool = True
    memory_url: str = "http://localhost:8080"
    memory_service_name: str = "turn-resolution-service"
    is_memory_iam_auth_enabled: bool = False
    memory_retrieve_timeout_seconds: float = 1.0
    memory_registration_retry_delay_seconds: float = 0.3
    memory_delivery_timeout_seconds: float = 1.0
    memory_relay_batch_limit: int = 50
    simulation_url: str = "http://localhost:8081"
    is_simulation_iam_auth_enabled: bool = False
    simulation_request_timeout_seconds: float = 5.0
    scene_message_max_chars: int = 600
    letter_seal_max_chars: int = 1200
    letter_scribe_instruction_max_chars: int = 300
    scene_reply_max_output_tokens: int = 400
    scene_decision_max_output_tokens: int = 120
    scene_reasoning_headroom_tokens: int = 1024
    scene_model_timeout_seconds: int = 45
    memory_relay_playthrough_limit: int = 20
    memory_relay_request_timeout_seconds: float = 5.0
    memory_relay_lease_margin_seconds: float = Field(default=5.0, gt=0)
    memory_retry_timeout_seconds: float = 30.0
    minigame_iframe_handshake_timeout_seconds: int = 20
    rule_check_queue_max: int = 8
    sensory_cue_max_per_turn: int = 3
    rule_check_tolerance_ms: int = 3500
    rule_check_hidden_grace_ms: int = 1500
    log_level: str = "INFO"
    log_format: str = "json"
    sse_ping_interval_seconds: int = 15
    turn_metrics_stat_snapshot_max_keys: int = 32

    is_rate_limit_enabled: bool = True
    # NOTE: Count of proxies appending to X-Forwarded-For in front of this
    # service; the client is that many entries from the right. Locally nginx
    # is the only hop (1); on Cloud Run the Google front end adds one (2).
    trusted_proxy_hops: int = 0
    internal_proxy_token: str = ""
    internal_service_token: str = ""
    summary_provider_timeout_seconds: int = Field(default=60, ge=1, le=60)
    summary_callback_timeout_seconds: float = Field(default=5.0, gt=0, le=10)
    rate_limit_exempt_firebase_uids: str = ""
    rate_limit_exempt_cache_seconds: int = 300
    rate_limit_window_seconds: int = 60
    rate_limit_turn_per_window: int = 10
    rate_limit_assistant_per_window: int = 10
    rate_limit_voice_per_window: int = 10
    rate_limit_memory_retry_per_window: int = 6
    rate_limit_scene_per_window: int = 12
    rate_limit_strategy_art_per_window: int = 12
    rate_limit_write_per_window: int = 60
    rate_limit_read_per_window: int = 120
    rate_limit_anonymous_per_window: int = 60
    rate_limit_ip_ceiling_per_window: int = 600
    quota_turn_per_user: int = 150
    quota_turn_global: int = 3000
    quota_scene_image_per_user: int = 20
    quota_scene_image_global: int = 300
    quota_strategy_art_per_user: int = 20
    quota_strategy_art_global: int = 300
    quota_strategy_dispatch_per_user: int = 60
    quota_strategy_dispatch_global: int = 900
    quota_strategy_proclamation_per_user: int = 60
    quota_strategy_proclamation_global: int = 900
    quota_strategy_event_per_user: int = 60
    quota_strategy_event_global: int = 900
    quota_tts_narration_per_user: int = 100
    quota_tts_narration_global: int = 1500
    quota_speech_to_text_per_user: int = 50
    quota_speech_to_text_global: int = 750
    quota_assistant_per_user: int = 100
    quota_assistant_global: int = 1500
    max_concurrent_streams_per_user: int = 3
    stream_lease_ttl_seconds: int = 60
    muse_api_key: str = ""
    muse_base_url: str = "https://api.meta.ai/v1"
    muse_image_model_name: str = "muse-image-1.0"
    muse_image_reasoning_strength: str = "low"
    image_generation_timeout_seconds: int = 90
    r2_account_id: str = ""
    r2_access_key_id: str = ""
    r2_secret_access_key: str = ""
    r2_bucket_name: str = ""
    r2_public_base_url: str = ""
    r2_endpoint_url: str = ""
    r2_region: str = "auto"
    r2_request_timeout_seconds: float = 30.0
    local_upload_dir: str = "uploads"
    firebase_credentials_path: str = ""
    speech_to_text_credentials_path: str = ""
    speech_to_text_project_id: str = ""
    muse_voice_model_name: str = "muse-voice-transcribe-1.0"
    speech_to_text_timeout_seconds: int = 10
    speech_to_text_max_phrase_hints: int = 100
    speech_to_text_max_phrase_length: int = 100
    voice_input_max_audio_bytes: int = 4 * 1024 * 1024
    voice_input_max_duration_seconds: int = 30
    text_to_speech_model: str = "gemini-3.1-flash-tts-preview"
    text_to_speech_timeout_seconds: int = 30
    text_to_speech_location: str = "global"
    should_use_service_account_for_tts: bool = False
    text_to_speech_default_voice: str = "Kore"
    voice_output_max_narration_chars: int = 4000

    @property
    def exempt_firebase_uids(self) -> frozenset[str]:
        return frozenset(
            uid.strip()
            for uid in self.rate_limit_exempt_firebase_uids.split(",")
            if uid.strip()
        )

    fish_api_key: str = ""
    fish_tts_model: str = "s2.1-pro-free"
    fish_katie_voice_id: str = "ecc977e5dca94390926fab1e0c2ba292"
    fish_timeout_seconds: float = 12.0

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
    def narration_model_name(self) -> str:
        if self.narration_provider == "anthropic":
            return self.anthropic_model_name
        return self.openai_compatible_model_name

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


settings = Settings()

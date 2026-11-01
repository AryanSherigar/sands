"""Memory service configuration module. The only place environment variables are read."""

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_MEMORY_DATABASE_URL = (
    "postgresql://memory_db:memory_db@localhost:5433/memory_db"
)
DEFAULT_MEMORY_TEST_DATABASE_URL = (
    "postgresql://memory_db:memory_db@127.0.0.1:5433/memory_test_db"
)
DEFAULT_DB_POOL_MIN_SIZE = 1
DEFAULT_DB_POOL_MAX_SIZE = 10
DEFAULT_SPAN_MAX_TOKENS = 300
DEFAULT_SPAN_CHARS_PER_TOKEN = 3
DEFAULT_INGEST_MAX_ITEMS_PER_REQUEST = 50
DEFAULT_EMBEDDING_MODEL_NAME = "text-embedding-005"
DEFAULT_EMBEDDING_MODEL_VERSION = "1"
DEFAULT_EMBEDDING_DIM = 768
DEFAULT_EMBEDDING_BATCH_SIZE = 100
DEFAULT_EMBEDDING_CLAIM_SIZE = 250
DEFAULT_EMBEDDING_CONCURRENCY = 4
DEFAULT_EMBEDDING_FAILURE_LIMIT = 3
DEFAULT_EMBEDDING_TRANSIENT_RETRIES = 1
DEFAULT_EMBEDDING_CLIENT_TIMEOUT_SECONDS = 20
DEFAULT_PROCESS_PENDING_DEADLINE_SECONDS = 50
DEFAULT_RECALL_BUDGET_TOKENS = 2000
DEFAULT_BRANCH_CANDIDATE_CAP = 40
DEFAULT_GRAPH_HOP2_MIN = 5
DEFAULT_HUB_EDGE_CAP = 20
DEFAULT_SINGLE_BRANCH_RANK_FLOOR = 20
DEFAULT_RRF_K = 60
DEFAULT_GRAPH_AND_EXACT_ONLY_BUDGET_SHARE = 0.4
DEFAULT_RECENT_WINDOW_TURNS = 6
DEFAULT_COMMITMENT_RECENT_RESOLUTION_TURNS = 20
DEFAULT_SEED_CAP = 30
DEFAULT_AMBIGUOUS_ALIAS_SEED_CAP = 5
DEFAULT_RETRIEVAL_EMBED_TIMEOUT_SECONDS = 0.3
DEFAULT_EXTRACTION_CONTEXT_TOKENS = 3000
DEFAULT_EXTRACTION_MODEL_NAME = "muse-spark-1.3"
DEFAULT_EXTRACTION_PROVIDER = "muse"
DEFAULT_MUSE_BASE_URL = "https://api.meta.ai/v1"
DEFAULT_MUSE_EXTRACTION_MAX_TOKENS = 8192
DEFAULT_MUSE_EXTRACTION_REASONING_EFFORT = "minimal"
DEFAULT_MUSE_EXTRACTION_TIMEOUT_SECONDS = 150
DEFAULT_ANTHROPIC_EXTRACTION_MODEL_NAME = "claude-haiku-5-5"
DEFAULT_ANTHROPIC_EXTRACTION_MAX_TOKENS = 8192
DEFAULT_ANTHROPIC_EXTRACTION_EFFORT = "low"
DEFAULT_EXTRACTION_BATCH_TURNS = 5
DEFAULT_EXTRACTION_PROMPT_VERSION = "extraction_v1"
DEFAULT_EXTRACTION_REJECT_NEGATED_PREDICATES = False
DEFAULT_EXTRACTION_CONTEXT_HAS_FACTS = True
DEFAULT_SUPERSESSION_RESOLUTION_MODE = "off"
DEFAULT_SUPERSESSION_CANDIDATE_CAP = 5
DEFAULT_SUPERSESSION_JUDGE_MAX_PAIRS = 8
DEFAULT_SUPERSESSION_FUNCTIONAL_PREDICATES = (
    "located_in",
    "lives_in",
    "costs",
    "leads",
    "run_by",
    "holds",
    "is_at",
    "owned_by",
)
DEFAULT_EXTRACTION_MAX_ATTEMPTS = 3
DEFAULT_EXTRACTION_BACKOFF_MINUTES = (1, 5, 15)
DEFAULT_EXTRACTION_CLIENT_TIMEOUT_SECONDS = 60
DEFAULT_EXTRACTION_WORKER_COUNT = 3
DEFAULT_EXTRACTION_STALLED_SECONDS = 180
DEFAULT_TEMPLATE_GC_FAILED_AGE_SECONDS = 86400
DEFAULT_EXTRACTION_ROSTER_CAP = 40
DEFAULT_EXTRACTION_LEASE_SECONDS = 180
DEFAULT_EMBEDDING_DEADLINE_SHARE = 0.6
DEFAULT_ENRICHMENT_MAX_INPUT_TOKENS = 600_000
DEFAULT_ENRICHMENT_CHUNK_TOKENS = 6000
DEFAULT_MEMORY_RETRY_DEADLINE_SECONDS = 25


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    memory_auth_mode: Literal["dev", "iam"] = "dev"
    memory_allowed_callers: str = ""
    memory_iam_audience: str = ""
    memory_database_url: str = DEFAULT_MEMORY_DATABASE_URL
    memory_test_database_url: str = DEFAULT_MEMORY_TEST_DATABASE_URL
    memory_db_pool_min_size: int = DEFAULT_DB_POOL_MIN_SIZE
    memory_db_pool_max_size: int = DEFAULT_DB_POOL_MAX_SIZE
    log_level: str = "INFO"
    span_max_tokens: int = DEFAULT_SPAN_MAX_TOKENS
    span_chars_per_token: int = DEFAULT_SPAN_CHARS_PER_TOKEN
    ingest_max_items_per_request: int = DEFAULT_INGEST_MAX_ITEMS_PER_REQUEST
    is_vertex_adc_enabled: bool = False
    vertex_project: str = ""
    vertex_location: str = "global"
    embedding_api_key: str = ""
    embedding_model_name: str = DEFAULT_EMBEDDING_MODEL_NAME
    embedding_model_version: str = DEFAULT_EMBEDDING_MODEL_VERSION
    embedding_dim: int = DEFAULT_EMBEDDING_DIM
    embedding_batch_size: int = DEFAULT_EMBEDDING_BATCH_SIZE
    embedding_claim_size: int = DEFAULT_EMBEDDING_CLAIM_SIZE
    embedding_concurrency: int = DEFAULT_EMBEDDING_CONCURRENCY
    embedding_failure_limit: int = DEFAULT_EMBEDDING_FAILURE_LIMIT
    embedding_transient_retries: int = DEFAULT_EMBEDDING_TRANSIENT_RETRIES
    embedding_client_timeout_seconds: int = DEFAULT_EMBEDDING_CLIENT_TIMEOUT_SECONDS
    process_pending_deadline_seconds: int = DEFAULT_PROCESS_PENDING_DEADLINE_SECONDS
    recall_budget_tokens: int = DEFAULT_RECALL_BUDGET_TOKENS
    branch_candidate_cap: int = DEFAULT_BRANCH_CANDIDATE_CAP
    graph_hop2_min: int = DEFAULT_GRAPH_HOP2_MIN
    hub_edge_cap: int = DEFAULT_HUB_EDGE_CAP
    single_branch_rank_floor: int = DEFAULT_SINGLE_BRANCH_RANK_FLOOR
    rrf_k: int = DEFAULT_RRF_K
    graph_and_exact_only_budget_share: float = DEFAULT_GRAPH_AND_EXACT_ONLY_BUDGET_SHARE
    recent_window_turns: int = DEFAULT_RECENT_WINDOW_TURNS
    commitment_recent_resolution_turns: int = DEFAULT_COMMITMENT_RECENT_RESOLUTION_TURNS
    seed_cap: int = DEFAULT_SEED_CAP
    ambiguous_alias_seed_cap: int = DEFAULT_AMBIGUOUS_ALIAS_SEED_CAP
    retrieval_embed_timeout_seconds: float = DEFAULT_RETRIEVAL_EMBED_TIMEOUT_SECONDS
    extraction_context_tokens: int = DEFAULT_EXTRACTION_CONTEXT_TOKENS
    extraction_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("extraction_api_key", "muse_api_key"),
    )
    extraction_model_name: str = DEFAULT_EXTRACTION_MODEL_NAME
    extraction_provider: Literal["anthropic", "muse"] = DEFAULT_EXTRACTION_PROVIDER
    muse_base_url: str = DEFAULT_MUSE_BASE_URL
    muse_extraction_max_tokens: int = DEFAULT_MUSE_EXTRACTION_MAX_TOKENS
    muse_extraction_reasoning_effort: str = DEFAULT_MUSE_EXTRACTION_REASONING_EFFORT
    muse_extraction_timeout_seconds: int = DEFAULT_MUSE_EXTRACTION_TIMEOUT_SECONDS
    anthropic_extraction_model_name: str = DEFAULT_ANTHROPIC_EXTRACTION_MODEL_NAME
    anthropic_extraction_max_tokens: int = DEFAULT_ANTHROPIC_EXTRACTION_MAX_TOKENS
    anthropic_extraction_effort: Literal["low", "medium", "high"] = (
        DEFAULT_ANTHROPIC_EXTRACTION_EFFORT
    )
    extraction_thinking_level: str | None = None
    extraction_prompt_version: Literal[
        "extraction_v1", "extraction_v2", "extraction_v3", "extraction_v4"
    ] = DEFAULT_EXTRACTION_PROMPT_VERSION
    extraction_reject_negated_predicates: bool = (
        DEFAULT_EXTRACTION_REJECT_NEGATED_PREDICATES
    )
    extraction_context_has_facts: bool = DEFAULT_EXTRACTION_CONTEXT_HAS_FACTS
    supersession_resolution_mode: Literal["off", "rules", "rules_and_judge"] = (
        DEFAULT_SUPERSESSION_RESOLUTION_MODE
    )
    supersession_candidate_cap: int = DEFAULT_SUPERSESSION_CANDIDATE_CAP
    supersession_judge_max_pairs: int = DEFAULT_SUPERSESSION_JUDGE_MAX_PAIRS
    supersession_functional_predicates: tuple[str, ...] = (
        DEFAULT_SUPERSESSION_FUNCTIONAL_PREDICATES
    )
    extraction_batch_turns: int = DEFAULT_EXTRACTION_BATCH_TURNS
    extraction_max_attempts: int = DEFAULT_EXTRACTION_MAX_ATTEMPTS
    extraction_backoff_minutes: tuple[int, ...] = DEFAULT_EXTRACTION_BACKOFF_MINUTES
    extraction_client_timeout_seconds: int = DEFAULT_EXTRACTION_CLIENT_TIMEOUT_SECONDS
    extraction_worker_count: int = DEFAULT_EXTRACTION_WORKER_COUNT
    extraction_stalled_seconds: int = DEFAULT_EXTRACTION_STALLED_SECONDS
    template_gc_failed_age_seconds: int = DEFAULT_TEMPLATE_GC_FAILED_AGE_SECONDS
    extraction_roster_cap: int = DEFAULT_EXTRACTION_ROSTER_CAP
    extraction_lease_seconds: int = DEFAULT_EXTRACTION_LEASE_SECONDS
    embedding_deadline_share: float = DEFAULT_EMBEDDING_DEADLINE_SHARE
    enrichment_max_input_tokens: int = DEFAULT_ENRICHMENT_MAX_INPUT_TOKENS
    enrichment_chunk_tokens: int = DEFAULT_ENRICHMENT_CHUNK_TOKENS
    memory_retry_deadline_seconds: int = DEFAULT_MEMORY_RETRY_DEADLINE_SECONDS

    @property
    def allowed_caller_emails(self) -> frozenset[str]:
        entries = (entry.strip() for entry in self.memory_allowed_callers.split(","))
        return frozenset(entry for entry in entries if entry)

    @model_validator(mode="after")
    def validate_auth_mode(self) -> "Settings":
        """Refuse to boot with an auth mode that is unsafe or incomplete."""
        is_iam_incomplete = self.memory_auth_mode == "iam" and not (
            self.allowed_caller_emails and self.memory_iam_audience
        )
        if is_iam_incomplete:
            raise ValueError(
                "MEMORY_AUTH_MODE=iam requires MEMORY_ALLOWED_CALLERS and "
                "MEMORY_IAM_AUDIENCE"
            )
        if self.memory_auth_mode == "dev" and self.environment == "production":
            raise ValueError(
                "MEMORY_AUTH_MODE=dev must not be used with ENVIRONMENT=production"
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

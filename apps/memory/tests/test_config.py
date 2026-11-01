"""Tests for app.config.Settings auth-mode/environment validation."""

import pytest
from app.config import (
    DEFAULT_AMBIGUOUS_ALIAS_SEED_CAP,
    DEFAULT_BRANCH_CANDIDATE_CAP,
    DEFAULT_COMMITMENT_RECENT_RESOLUTION_TURNS,
    DEFAULT_EXTRACTION_CONTEXT_TOKENS,
    DEFAULT_GRAPH_AND_EXACT_ONLY_BUDGET_SHARE,
    DEFAULT_GRAPH_HOP2_MIN,
    DEFAULT_HUB_EDGE_CAP,
    DEFAULT_RECALL_BUDGET_TOKENS,
    DEFAULT_RECENT_WINDOW_TURNS,
    DEFAULT_RETRIEVAL_EMBED_TIMEOUT_SECONDS,
    DEFAULT_RRF_K,
    DEFAULT_SEED_CAP,
    DEFAULT_SINGLE_BRANCH_RANK_FLOOR,
    Settings,
)
from pydantic import ValidationError


def test_dev_auth_in_production_raises() -> None:
    with pytest.raises(ValidationError):
        Settings(memory_auth_mode="dev", environment="production")


def test_iam_auth_requires_allowed_callers() -> None:
    with pytest.raises(ValidationError):
        Settings(
            memory_auth_mode="iam",
            environment="production",
            memory_iam_audience="https://memory.example.test",
        )


def test_iam_auth_requires_an_audience() -> None:
    with pytest.raises(ValidationError):
        Settings(
            memory_auth_mode="iam",
            environment="production",
            memory_allowed_callers="trs@project.iam.gserviceaccount.com",
        )


def test_iam_auth_with_callers_and_audience_is_valid_in_production() -> None:
    settings = Settings(
        memory_auth_mode="iam",
        environment="production",
        memory_allowed_callers=" a@x.com, ,b@x.com ",
        memory_iam_audience="https://memory.example.test",
    )

    assert settings.allowed_caller_emails == frozenset({"a@x.com", "b@x.com"})


def test_dev_auth_in_development_is_valid() -> None:
    settings = Settings(memory_auth_mode="dev", environment="development")
    assert settings.memory_auth_mode == "dev"
    assert settings.environment == "development"


def test_retrieval_defaults() -> None:
    settings = Settings()
    assert settings.recall_budget_tokens == DEFAULT_RECALL_BUDGET_TOKENS
    assert settings.branch_candidate_cap == DEFAULT_BRANCH_CANDIDATE_CAP
    assert settings.graph_hop2_min == DEFAULT_GRAPH_HOP2_MIN
    assert settings.hub_edge_cap == DEFAULT_HUB_EDGE_CAP
    assert settings.single_branch_rank_floor == DEFAULT_SINGLE_BRANCH_RANK_FLOOR
    assert settings.rrf_k == DEFAULT_RRF_K
    assert settings.graph_and_exact_only_budget_share == (
        DEFAULT_GRAPH_AND_EXACT_ONLY_BUDGET_SHARE
    )
    assert settings.recent_window_turns == DEFAULT_RECENT_WINDOW_TURNS
    assert settings.commitment_recent_resolution_turns == (
        DEFAULT_COMMITMENT_RECENT_RESOLUTION_TURNS
    )
    assert settings.seed_cap == DEFAULT_SEED_CAP
    assert settings.ambiguous_alias_seed_cap == DEFAULT_AMBIGUOUS_ALIAS_SEED_CAP
    assert settings.retrieval_embed_timeout_seconds == (
        DEFAULT_RETRIEVAL_EMBED_TIMEOUT_SECONDS
    )
    assert settings.extraction_context_tokens == DEFAULT_EXTRACTION_CONTEXT_TOKENS


def test_extraction_prompt_version_defaults_to_v1_and_accepts_v2() -> None:
    from app.models.extraction import EXTRACTION_PROMPT_VERSION

    assert Settings().extraction_prompt_version == EXTRACTION_PROMPT_VERSION
    assert Settings(
        extraction_prompt_version="extraction_v2"
    ).extraction_prompt_version == ("extraction_v2")


def test_unknown_extraction_prompt_version_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(extraction_prompt_version="extraction_v99")


def test_extraction_v3_is_selectable_and_negation_rejection_defaults_off() -> None:
    from app.config import Settings

    assert Settings(
        extraction_prompt_version="extraction_v3"
    ).extraction_prompt_version == ("extraction_v3")
    assert Settings().extraction_reject_negated_predicates is False
    assert Settings(
        extraction_reject_negated_predicates=True
    ).extraction_reject_negated_predicates


def test_supersession_resolution_is_off_by_default_and_modes_are_validated() -> None:
    assert Settings().supersession_resolution_mode == "off"
    assert Settings(
        supersession_resolution_mode="rules_and_judge"
    ).supersession_resolution_mode == ("rules_and_judge")
    with pytest.raises(ValidationError):
        Settings(supersession_resolution_mode="always")


def test_extraction_v4_is_selectable_and_context_keeps_facts_by_default() -> None:
    assert Settings(
        extraction_prompt_version="extraction_v4"
    ).extraction_prompt_version == ("extraction_v4")
    assert Settings().extraction_context_has_facts is True

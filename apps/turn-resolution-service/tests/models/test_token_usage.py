"""Tests for TokenUsage model."""

from app.models.token_usage import TokenUsage


def test_token_usage_defaults() -> None:
    usage = TokenUsage()
    assert usage.prompt_tokens == 0
    assert usage.completion_tokens == 0
    assert usage.model_name == ""
    assert usage.total_tokens == 0


def test_token_usage_total_calculation() -> None:
    usage = TokenUsage(
        prompt_tokens=150,
        completion_tokens=50,
        model_name="gemini-2.5-flash",
    )
    assert usage.total_tokens == 200
    assert usage.model_name == "gemini-2.5-flash"

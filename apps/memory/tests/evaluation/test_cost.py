import pytest
from eval.errors import BudgetExceededError, PricesMissingError
from eval.prices import (
    ModelPrice,
    PriceTable,
    RunUsage,
    assert_within_budget,
    compute_cost,
    load_prices,
)

PRICES = PriceTable(
    effective_date="2027-01-02",
    models={
        "emb": ModelPrice(per_million_characters=25.0),
        "ext": ModelPrice(input_per_million_tokens=0.1, output_per_million_tokens=0.4),
    },
)
USAGE = RunUsage(
    extraction_model="ext",
    extraction_input_tokens=2_000_000,
    extraction_output_tokens=500_000,
    embedding_model="emb",
    characters_embedded=1_000_000,
    query_characters=200_000,
)


def test_cost_arithmetic_from_usage_and_prices() -> None:
    cost = compute_cost(USAGE, PRICES)
    assert cost.extraction_usd == pytest.approx(0.4)
    assert cost.embedding_usd == pytest.approx(25.0)
    assert cost.query_embedding_usd == pytest.approx(5.0)
    assert cost.total_usd == pytest.approx(30.4)


def test_unfilled_price_refuses_to_compute() -> None:
    unfilled = PriceTable(
        effective_date="unset",
        models={"emb": ModelPrice(), "ext": ModelPrice()},
    )
    with pytest.raises(PricesMissingError):
        compute_cost(USAGE, unfilled)


def test_shipped_price_table_covers_the_pinned_models() -> None:
    from app.config import Settings

    settings = Settings()
    usage = RunUsage(
        extraction_model=settings.extraction_model_name,
        embedding_model=settings.embedding_model_name,
    )
    cost = compute_cost(usage, load_prices())
    assert cost.total_usd == 0.0


def test_unknown_model_refuses_to_compute() -> None:
    with pytest.raises(PricesMissingError):
        compute_cost(USAGE.model_copy(update={"extraction_model": "other"}), PRICES)


def test_budget_guard_fires_above_the_limit_only() -> None:
    cost = compute_cost(USAGE, PRICES)
    with pytest.raises(BudgetExceededError):
        assert_within_budget(cost, limit_usd=2.0)
    assert_within_budget(cost, limit_usd=100.0)

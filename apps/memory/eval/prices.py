"""Price table and cost arithmetic from recorded usage."""

from pathlib import Path

from pydantic import BaseModel

from eval.errors import BudgetExceededError, PricesMissingError

PRICES_FILE = Path(__file__).parent / "prices.json"
TOKENS_PER_MILLION = 1_000_000
CHARACTERS_PER_MILLION = 1_000_000
DEFAULT_BUDGET_USD = 2.0


class ModelPrice(BaseModel):
    input_per_million_tokens: float | None = None
    output_per_million_tokens: float | None = None
    per_million_characters: float | None = None


class PriceTable(BaseModel):
    effective_date: str
    note: str = ""
    models: dict[str, ModelPrice]


class RunUsage(BaseModel):
    extraction_model: str
    extraction_input_tokens: int = 0
    extraction_output_tokens: int = 0
    embedding_model: str
    characters_embedded: int = 0
    query_characters: int = 0


class CostBreakdown(BaseModel):
    extraction_usd: float
    embedding_usd: float
    query_embedding_usd: float

    @property
    def total_usd(self) -> float:
        return self.extraction_usd + self.embedding_usd + self.query_embedding_usd


def load_prices(path: Path = PRICES_FILE) -> PriceTable:
    return PriceTable.model_validate_json(path.read_text(encoding="utf-8"))


def _price_of(prices: PriceTable, model: str) -> ModelPrice:
    if model not in prices.models:
        raise PricesMissingError(f"No price entry for model {model}")
    return prices.models[model]


def _required(value: float | None, model: str, field_name: str) -> float:
    if value is None:
        raise PricesMissingError(f"Price {field_name} for {model} is not filled in")
    return value


def compute_cost(usage: RunUsage, prices: PriceTable) -> CostBreakdown:
    extraction = _price_of(prices, usage.extraction_model)
    embedding = _price_of(prices, usage.embedding_model)
    input_rate = _required(
        extraction.input_per_million_tokens, usage.extraction_model, "input"
    )
    output_rate = _required(
        extraction.output_per_million_tokens, usage.extraction_model, "output"
    )
    character_rate = _required(
        embedding.per_million_characters, usage.embedding_model, "characters"
    )
    return CostBreakdown(
        extraction_usd=(
            usage.extraction_input_tokens * input_rate
            + usage.extraction_output_tokens * output_rate
        )
        / TOKENS_PER_MILLION,
        embedding_usd=usage.characters_embedded
        * character_rate
        / CHARACTERS_PER_MILLION,
        query_embedding_usd=usage.query_characters
        * character_rate
        / CHARACTERS_PER_MILLION,
    )


def assert_within_budget(
    cost: CostBreakdown, limit_usd: float = DEFAULT_BUDGET_USD
) -> None:
    if cost.total_usd > limit_usd:
        raise BudgetExceededError(
            f"Run cost ${cost.total_usd:.4f} passed the ${limit_usd:.2f} abort limit"
        )


def assert_prices_ready(usage: RunUsage, prices: PriceTable) -> None:
    compute_cost(usage, prices)

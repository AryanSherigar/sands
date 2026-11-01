import pytest
from app.models.world_faction import FactionState, LoanState
from pydantic import ValidationError
from strategy_contracts.enums import TaxRate


def _faction(**overrides: object) -> FactionState:
    fields: dict[str, object] = {
        "id": "house_ashford",
        "leader_id": "mira",
        "treasury": 120,
        "stability": 60,
        "war_exhaustion": 0,
        "reputation": 0,
        "tax_rate": TaxRate.NORMAL,
        "orders_remaining": 6,
        "is_player": False,
    }
    fields.update(overrides)
    return FactionState.model_validate(fields)


def test_negative_treasury_is_accepted() -> None:
    assert _faction(treasury=-50).treasury == -50


def test_stability_above_100_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _faction(stability=101)


def test_faction_round_trips_with_loan() -> None:
    faction = _faction(
        loans=[LoanState(principal=50, interest_percent=10, turns_remaining=6)]
    )
    assert FactionState.model_validate_json(faction.model_dump_json()) == faction

import pytest
from app.models.world_region import (
    ImprovementState,
    OccupationState,
    RegionIntel,
    RegionState,
)
from pydantic import ValidationError
from strategy_contracts.enums import ImprovementKind


def _region(**overrides: object) -> RegionState:
    fields: dict[str, object] = {
        "id": "ashford",
        "owner_id": "house_ashford",
        "population": 900,
        "wealth": 70,
        "manpower": 120,
        "unrest": 10,
        "garrison": 60,
        "faith_id": "old_faith",
    }
    fields.update(overrides)
    return RegionState.model_validate(fields)


def test_region_round_trips_with_nested_state() -> None:
    region = _region(
        improvements=[ImprovementState(kind=ImprovementKind.FORT, turns_remaining=2)],
        occupation=OccupationState(occupier_id="house_dunwick", siege_progress=1),
    )
    assert RegionState.model_validate_json(region.model_dump_json()) == region


def test_unrest_above_100_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _region(unrest=101)


def test_extra_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _region(secret=1)


def test_intel_round_trips() -> None:
    intel = RegionIntel(
        last_seen_turn=3, owner_id=None, garrison_low=10, garrison_high=40
    )
    assert RegionIntel.model_validate_json(intel.model_dump_json()) == intel

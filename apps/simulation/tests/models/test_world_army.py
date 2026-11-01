import pytest
from app.models.world_army import ArmyOrderState, ArmyState, MarchState
from pydantic import ValidationError
from strategy_contracts.enums import OrderKind, TroopType


def _army(**overrides: object) -> ArmyState:
    fields: dict[str, object] = {
        "id": "army_ashford_1",
        "owner_id": "house_ashford",
        "troops": {TroopType.INFANTRY: 300},
        "morale": 70,
        "location_id": "ashford",
    }
    fields.update(overrides)
    return ArmyState.model_validate(fields)


def test_army_round_trips_with_order() -> None:
    army = _army(order=ArmyOrderState(kind=OrderKind.MOVE_ARMY, target_id="brennmoor"))
    assert ArmyState.model_validate_json(army.model_dump_json()) == army


def test_negative_troops_are_rejected() -> None:
    with pytest.raises(ValidationError):
        _army(troops={TroopType.INFANTRY: -1})


def _march(**overrides: object) -> MarchState:
    fields: dict[str, object] = {
        "from_id": "ashford",
        "to_id": "brennmoor",
        "route": ["carrow_vale"],
        "leg_progress": 40,
    }
    fields.update(overrides)
    return MarchState.model_validate(fields)


def test_army_round_trips_with_a_march() -> None:
    army = _army(march=_march())
    assert ArmyState.model_validate_json(army.model_dump_json()) == army


def test_march_must_start_where_the_army_stands() -> None:
    with pytest.raises(ValidationError):
        _army(march=_march(from_id="brennmoor", to_id="ashford", route=[]))


def test_march_rejects_negative_progress() -> None:
    with pytest.raises(ValidationError):
        _march(leg_progress=-1)


@pytest.mark.parametrize(
    "fields",
    [
        {"to_id": "ashford"},
        {"route": ["ashford"]},
        {"route": ["brennmoor"]},
        {"route": ["carrow_vale", "carrow_vale"]},
    ],
)
def test_march_rejects_a_route_that_revisits_a_region(
    fields: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        _march(**fields)


def test_march_rejects_invalid_region_ids() -> None:
    with pytest.raises(ValidationError):
        _march(to_id="Not An Id")


def test_march_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        _march(speed=3)


def test_halted_march_cannot_carry_a_route() -> None:
    with pytest.raises(ValidationError):
        _march(is_halted=True)


def test_halted_march_without_a_route_is_valid() -> None:
    assert _march(is_halted=True, route=[]).is_halted is True


def test_returning_march_round_trips_and_may_route_back_through_its_far_end() -> None:
    march = _march(is_returning=True, route=["carrow_vale", "brennmoor"])
    assert MarchState.model_validate_json(march.model_dump_json()) == march


def test_returning_march_needs_progress_to_walk_back() -> None:
    with pytest.raises(ValidationError):
        _march(is_returning=True, leg_progress=0)


def test_returning_march_cannot_also_be_halted() -> None:
    with pytest.raises(ValidationError):
        _march(is_returning=True, is_halted=True, route=[])


def test_returning_route_may_pass_through_the_far_end_of_the_road() -> None:
    assert _march(is_returning=True, route=["brennmoor"]).route == ["brennmoor"]


def test_returning_route_may_not_revisit_the_origin() -> None:
    with pytest.raises(ValidationError):
        _march(is_returning=True, route=["ashford"])

import pytest
from pydantic import ValidationError
from strategy_contracts.enums import OrderKind, RouteStyle, Terrain, TroopType
from strategy_contracts.scenario import MovementTuning, StrategyScenario, Tuning


def test_defaults_cover_every_terrain_and_troop_type() -> None:
    tuning = MovementTuning()
    assert set(tuning.terrain_costs) == set(Terrain)
    assert set(tuning.troop_type_penalty_percent) == set(TroopType)


def test_default_costs_are_positive_whole_numbers() -> None:
    tuning = MovementTuning()
    assert all(cost > 0 for cost in tuning.terrain_costs.values())
    assert tuning.budget_per_turn > 0


def test_terrain_costs_missing_a_terrain_are_refused() -> None:
    with pytest.raises(ValidationError):
        MovementTuning(terrain_costs={Terrain.PLAIN: 100})


def test_troop_penalties_missing_a_type_are_refused() -> None:
    with pytest.raises(ValidationError):
        MovementTuning(troop_type_penalty_percent={TroopType.INFANTRY: 0})


@pytest.mark.parametrize(
    "field", ["budget_per_turn", "size_step_troops", "low_morale_threshold"]
)
def test_zero_is_refused_where_it_would_divide_or_stall(field: str) -> None:
    with pytest.raises(ValidationError):
        MovementTuning(**{field: 0})


def test_zero_terrain_cost_is_refused() -> None:
    costs = MovementTuning().terrain_costs | {Terrain.PLAIN: 0}
    with pytest.raises(ValidationError):
        MovementTuning(terrain_costs=costs)


@pytest.mark.parametrize(
    "field", ["road_discount_percent", "winter_penalty_percent", "size_cap_percent"]
)
def test_percentages_beyond_bounds_are_refused(field: str) -> None:
    with pytest.raises(ValidationError):
        MovementTuning(**{field: 1001})


def test_extra_fields_are_refused() -> None:
    with pytest.raises(ValidationError):
        MovementTuning(unknown_field=1)


def test_tuning_carries_default_movement_and_round_trips() -> None:
    tuning = Tuning()
    assert tuning.movement == MovementTuning()
    restored = Tuning.model_validate_json(tuning.model_dump_json())
    assert restored == tuning


def test_scenario_without_movement_key_still_parses() -> None:
    document = StrategyScenario().model_dump(mode="json")
    del document["tuning"]["movement"]
    assert StrategyScenario.model_validate(document).tuning.movement == MovementTuning()


def test_halt_army_is_a_free_order_by_default() -> None:
    assert Tuning().order_costs[OrderKind.HALT_ARMY] == 0


def test_route_penalties_have_defaults_and_cannot_be_negative() -> None:
    tuning = MovementTuning()
    assert tuning.safest_hazard_penalty == 200
    assert tuning.roads_off_road_penalty == 50
    for field in ("safest_hazard_penalty", "roads_off_road_penalty"):
        with pytest.raises(ValidationError):
            MovementTuning(**{field: -1})


def test_route_style_has_the_three_player_choices() -> None:
    assert {style.value for style in RouteStyle} == {"fastest", "safest", "roads"}

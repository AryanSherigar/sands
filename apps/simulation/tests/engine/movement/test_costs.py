import pytest
from app.engine.movement.costs import (
    MIN_LEG_COST,
    leg_cost,
    months_of_turn,
)
from app.engine.movement.map_index import build_map_index
from app.models.world_clock import TurnClock
from strategy_contracts.enums import Terrain, TroopType
from strategy_contracts.scenario import MovementTuning

from tests.engine.movement.builders import (
    FACTION_A,
    SPRING_START_MONTH,
    SUMMER_START_MONTH,
    WINTER_START_MONTH,
    make_army,
    make_map,
)

TUNING = MovementTuning()


def _index(terrain: Terrain = Terrain.PLAIN, has_road: bool = False):
    roads = [("reg_a", "reg_b")] if has_road else []
    map_document = make_map(
        {"reg_a": Terrain.PLAIN, "reg_b": terrain}, [("reg_a", "reg_b")], roads
    )
    return build_map_index(map_document)


def _clock(start_month: int, turn: int = 0) -> TurnClock:
    return TurnClock(turn=turn, start_year=1000, start_month=start_month)


def _cost(
    army=None,
    terrain: Terrain = Terrain.PLAIN,
    has_road: bool = False,
    start_month: int = SUMMER_START_MONTH,
    tuning: MovementTuning = TUNING,
    turn: int = 0,
):
    army = army or make_army("army_a", FACTION_A, "reg_a")
    return leg_cost(
        _index(terrain, has_road),
        army,
        _clock(start_month, turn),
        tuning,
        "reg_a",
        "reg_b",
    )


def _reasons(cost) -> dict[str, int]:
    return {adjustment.reason: adjustment.percent for adjustment in cost.adjustments}


@pytest.mark.parametrize("terrain", list(Terrain))
def test_base_cost_follows_the_destination_terrain(terrain: Terrain) -> None:
    cost = _cost(terrain=terrain)
    assert cost.base == TUNING.terrain_costs[terrain]
    assert cost.total == cost.base
    assert cost.adjustments == ()


@pytest.mark.parametrize("terrain", list(Terrain))
def test_a_road_always_makes_the_leg_cheaper(terrain: Terrain) -> None:
    without_road = _cost(terrain=terrain)
    with_road = _cost(terrain=terrain, has_road=True)
    assert with_road.total < without_road.total
    assert _reasons(with_road) == {"road": -TUNING.road_discount_percent}


def test_road_is_found_whichever_way_the_pair_is_listed() -> None:
    map_document = make_map(
        {"reg_a": Terrain.PLAIN, "reg_b": Terrain.PLAIN},
        [("reg_a", "reg_b")],
        [("reg_b", "reg_a")],
    )
    cost = leg_cost(
        build_map_index(map_document),
        make_army("army_a", FACTION_A, "reg_a"),
        _clock(SUMMER_START_MONTH),
        TUNING,
        "reg_a",
        "reg_b",
    )
    assert _reasons(cost) == {"road": -50}


@pytest.mark.parametrize(
    ("start_month", "turn", "expected_months"),
    [
        (1, 0, (1, 2)),
        (3, 1, (5, 6)),
        (11, 0, (11, 12)),
        (12, 0, (12, 1)),
        (12, 1, (2, 3)),
        (11, 6, (11, 12)),
        (7, 3, (1, 2)),
    ],
)
def test_months_of_turn_wraps_the_year(
    start_month: int, turn: int, expected_months: tuple[int, int]
) -> None:
    assert months_of_turn(_clock(start_month, turn)) == expected_months


@pytest.mark.parametrize("start_month", range(1, 13))
@pytest.mark.parametrize("turn", range(6))
def test_every_turn_covers_two_consecutive_months(start_month: int, turn: int) -> None:
    first, second = months_of_turn(_clock(start_month, turn))
    assert second == first % 12 + 1


def test_a_fully_winter_turn_adds_the_whole_winter_penalty() -> None:
    cost = _cost(start_month=1)
    assert _reasons(cost) == {"winter": 50}
    assert cost.total == 150


def test_a_turn_straddling_autumn_and_winter_adds_half_the_penalty() -> None:
    cost = _cost(start_month=WINTER_START_MONTH - 1)
    assert _reasons(cost) == {"winter": 25}


def test_year_wrap_from_december_to_january_is_fully_winter() -> None:
    assert _reasons(_cost(start_month=WINTER_START_MONTH)) == {"winter": 50}


def test_a_turn_straddling_winter_and_spring_pays_both_halves() -> None:
    cost = _cost(start_month=2, turn=0)
    assert _reasons(cost) == {"winter": 25, "spring": 10}


def test_spring_mud_adds_the_spring_penalty() -> None:
    assert _reasons(_cost(start_month=SPRING_START_MONTH)) == {"spring": 20}


def test_summer_has_no_season_penalty() -> None:
    assert _reasons(_cost(start_month=SUMMER_START_MONTH)) == {}


def test_winter_is_never_cheaper_than_summer_in_any_month() -> None:
    summer = _cost(start_month=SUMMER_START_MONTH).total
    for month in range(1, 13):
        assert _cost(start_month=month).total >= summer


@pytest.mark.parametrize(
    ("troops", "expected_percent"),
    [(999, None), (1000, 10), (1999, 10), (2500, 20), (4999, 40), (5000, 50)],
)
def test_size_slows_by_steps(troops: int, expected_percent: int | None) -> None:
    army = make_army("army_a", FACTION_A, "reg_a", {TroopType.INFANTRY: troops})
    reasons = _reasons(_cost(army))
    assert reasons.get("size") == expected_percent


def test_size_penalty_is_capped() -> None:
    army = make_army("army_a", FACTION_A, "reg_a", {TroopType.INFANTRY: 90_000})
    assert _reasons(_cost(army))["size"] == TUNING.size_cap_percent


def test_size_counts_every_troop_type() -> None:
    troops = {TroopType.INFANTRY: 600, TroopType.CAVALRY: 600}
    army = make_army("army_a", FACTION_A, "reg_a", troops)
    assert _reasons(_cost(army))["size"] == 10


def test_cavalry_only_army_is_faster_than_infantry() -> None:
    cavalry = make_army("army_a", FACTION_A, "reg_a", {TroopType.CAVALRY: 100})
    assert _reasons(_cost(cavalry)) == {"troop_mix": -20}
    assert _cost(cavalry).total < _cost().total


def test_siege_gear_slows_the_whole_army() -> None:
    troops = {TroopType.INFANTRY: 100, TroopType.ARCHERS_SIEGE: 10}
    army = make_army("army_a", FACTION_A, "reg_a", troops)
    assert _reasons(_cost(army)) == {"troop_mix": 30}


def test_mixed_cavalry_and_infantry_moves_at_the_infantry_pace() -> None:
    troops = {TroopType.INFANTRY: 100, TroopType.CAVALRY: 100}
    army = make_army("army_a", FACTION_A, "reg_a", troops)
    assert "troop_mix" not in _reasons(_cost(army))


def test_a_troop_type_with_no_soldiers_does_not_set_the_pace() -> None:
    troops = {TroopType.INFANTRY: 100, TroopType.ARCHERS_SIEGE: 0}
    army = make_army("army_a", FACTION_A, "reg_a", troops)
    assert "troop_mix" not in _reasons(_cost(army))


@pytest.mark.parametrize(
    ("morale", "expected_percent"),
    [(100, None), (40, None), (39, 0), (30, 7), (20, 15), (0, 30)],
)
def test_low_morale_slows_proportionally(
    morale: int, expected_percent: int | None
) -> None:
    army = make_army("army_a", FACTION_A, "reg_a", morale=morale)
    reasons = _reasons(_cost(army))
    assert reasons.get("morale") == (expected_percent or None)


def test_lower_morale_is_never_faster() -> None:
    totals = [
        _cost(make_army("army_a", FACTION_A, "reg_a", morale=morale)).total
        for morale in range(100, -1, -1)
    ]
    assert totals == sorted(totals)


def test_adjustments_add_together_before_applying_to_the_base() -> None:
    troops = {TroopType.CAVALRY: 3000}
    army = make_army("army_a", FACTION_A, "reg_a", troops, morale=20)
    cost = _cost(army, Terrain.MOUNTAIN, has_road=True, start_month=1)
    assert _reasons(cost) == {
        "road": -50,
        "winter": 50,
        "size": 30,
        "troop_mix": -20,
        "morale": 15,
    }
    assert cost.total == 250 * (100 + 25) // 100


def test_cost_never_drops_below_the_floor() -> None:
    tuning = MovementTuning(
        road_discount_percent=1000,
        terrain_costs={terrain: 1 for terrain in Terrain},
    )
    cost = _cost(has_road=True, tuning=tuning)
    assert cost.total == MIN_LEG_COST


def test_a_discount_larger_than_the_base_still_leaves_a_positive_cost() -> None:
    tuning = MovementTuning(road_discount_percent=1000)
    assert _cost(has_road=True, tuning=tuning).total >= MIN_LEG_COST


def test_creator_tuning_changes_the_cost() -> None:
    tuning = MovementTuning(terrain_costs=TUNING.terrain_costs | {Terrain.PLAIN: 40})
    assert _cost(tuning=tuning).total == 40


def test_every_adjustment_carries_a_reason_key() -> None:
    cost = _cost(has_road=True, start_month=1)
    assert all(adjustment.reason for adjustment in cost.adjustments)

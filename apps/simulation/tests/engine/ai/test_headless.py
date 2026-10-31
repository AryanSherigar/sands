from app.engine.ai.headless import (
    FLAG_BANKRUPTCY,
    FLAG_ENDLESS_WAR,
    FLAG_SNOWBALL,
    FLAG_STAGNATION,
    FLAG_UNREST,
    OBSERVER_FACTION_ID,
    TurnSample,
    detect_flags,
    observer_scenario,
    run_headless,
)
from app.models.world_diplomacy import WarState
from app.models.world_player import PlayerRuler
from strategy_contracts.examples import load_three_crowns_expanded

from tests.engine.diplomacy.builders import make_world

SCENARIO = load_three_crowns_expanded()
RULER = PlayerRuler(
    name="Valdren", trait_ids=["honorable", "cautious"], ambition_ids=["ambition_peace"]
)
SHORT_RUN = 6


def _sample(
    turn: int,
    regions: dict[str, int] | None = None,
    treasury: int = 100,
    stability: int = 60,
    planned: int = 5,
) -> TurnSample:
    return TurnSample(
        turn=turn,
        regions_by_owner=regions or {"a": 3, "b": 3, "c": 3},
        treasury_by_faction={"a": treasury, "b": 100, OBSERVER_FACTION_ID: 10**6},
        stability_by_faction={"a": stability, "b": 60, OBSERVER_FACTION_ID: 50},
        war_count=0,
        planned_orders=planned,
    )


def _flags(samples: list[TurnSample], world=None) -> list[str]:
    return detect_flags(world or make_world(), samples)


def test_a_healthy_series_raises_no_flags() -> None:
    assert _flags([_sample(turn) for turn in range(20)]) == []


def test_one_owner_holding_most_regions_is_a_snowball() -> None:
    samples = [_sample(turn, regions={"a": 9, "b": 1}) for turn in range(3)]

    assert FLAG_SNOWBALL in _flags(samples)


def test_a_faction_broke_for_eight_turns_is_a_bankruptcy_spiral() -> None:
    broke = [_sample(turn, treasury=0) for turn in range(8)]

    assert FLAG_BANKRUPTCY in _flags(broke)
    assert FLAG_BANKRUPTCY not in _flags(broke[:7])


def test_a_short_dip_is_not_a_bankruptcy_spiral() -> None:
    series = [_sample(turn, treasury=0 if turn % 4 == 0 else 50) for turn in range(20)]

    assert FLAG_BANKRUPTCY not in _flags(series)


def test_collapsed_stability_for_eight_turns_is_an_unrest_collapse() -> None:
    series = [_sample(turn, stability=3) for turn in range(8)]

    assert FLAG_UNREST in _flags(series)


def test_no_orders_for_ten_turns_is_stagnation() -> None:
    series = [_sample(turn, planned=0) for turn in range(10)]

    assert FLAG_STAGNATION in _flags(series)
    assert FLAG_STAGNATION not in _flags(series[:9])


def test_a_war_older_than_forty_turns_is_endless() -> None:
    world = make_world()
    world.clock.turn = 60
    world.wars.append(
        WarState(
            id="war_1", attacker_id="house_aa", defender_id="house_bb", started_turn=10
        )
    )

    assert FLAG_ENDLESS_WAR in _flags([_sample(60)], world)


def test_the_observer_never_trips_a_flag() -> None:
    sample = TurnSample(
        turn=1,
        regions_by_owner={OBSERVER_FACTION_ID: 10},
        treasury_by_faction={OBSERVER_FACTION_ID: 0},
        stability_by_faction={OBSERVER_FACTION_ID: 0},
        war_count=0,
        planned_orders=1,
    )

    assert FLAG_BANKRUPTCY not in _flags([sample] * 10)
    assert FLAG_UNREST not in _flags([sample] * 10)


def test_the_observer_is_added_to_a_copy() -> None:
    before = len(SCENARIO.factions)

    observed = observer_scenario(SCENARIO)

    assert len(SCENARIO.factions) == before
    assert OBSERVER_FACTION_ID in {faction.id for faction in observed.factions}


def test_runs_are_deterministic_and_cover_every_real_faction() -> None:
    first = run_headless(SCENARIO, 7, SHORT_RUN, RULER)
    second = run_headless(SCENARIO, 7, SHORT_RUN, RULER)

    assert first.final_hash == second.final_hash
    assert first.order_fingerprints == second.order_fingerprints
    assert first.turns_run == SHORT_RUN
    assert "paused" not in first.flags


def test_different_seeds_give_different_games() -> None:
    first = run_headless(SCENARIO, 1, SHORT_RUN, RULER)
    second = run_headless(SCENARIO, 2, SHORT_RUN, RULER)

    assert first.final_hash != second.final_hash

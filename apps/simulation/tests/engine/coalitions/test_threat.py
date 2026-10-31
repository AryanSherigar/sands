from app.engine.coalitions.ledger import record_atrocity, record_conquest
from app.engine.coalitions.threat import compute_threat
from app.models.world_diplomacy import OathbreakerMark

from tests.engine.coalitions.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.coalition


def _region(world, faction_id=PLAYER):
    return next(
        key
        for key, item in sorted(world.regions.items())
        if item.owner_id == faction_id
    )


def test_a_peaceful_world_has_no_conquest_atrocity_or_treaty_threat() -> None:
    world = make_world()

    reading = compute_threat(world, SCENARIO, PLAYER)

    assert (reading.conquest, reading.treaty_breaking, reading.atrocity) == (0, 0, 0)


def test_conquests_inside_the_window_count_by_wealth() -> None:
    world = make_world()
    region_id = _region(world)
    record_conquest(world, SCENARIO, PLAYER, region_id)

    reading = compute_threat(world, SCENARIO, PLAYER)

    assert reading.conquest == world.regions[region_id].wealth // (
        TUNING.conquest_wealth_divisor
    )


def test_conquests_outside_the_window_are_forgotten() -> None:
    world = make_world()
    record_conquest(world, SCENARIO, PLAYER, _region(world))
    world.clock.turn += TUNING.conquest_window_turns

    assert compute_threat(world, SCENARIO, PLAYER).conquest == 0


def test_a_conquest_costs_the_conqueror_reputation() -> None:
    world = make_world()
    before = world.factions[PLAYER].reputation

    record_conquest(world, SCENARIO, PLAYER, _region(world))

    assert world.factions[PLAYER].reputation == before - TUNING.conquest_reputation_cost


def test_oathbreaker_mark_and_groundless_war_add_treaty_threat() -> None:
    world = make_world()
    world.oathbreakers.append(OathbreakerMark(faction_id=WRATHFUL_RIVAL, since_turn=0))
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)

    reading = compute_threat(world, SCENARIO, WRATHFUL_RIVAL)

    assert reading.treaty_breaking == (
        TUNING.oathbreaker_threat + TUNING.no_ground_war_threat
    )


def test_atrocities_add_threat_each() -> None:
    world = make_world()
    record_atrocity(world, PLAYER)
    record_atrocity(world, PLAYER)

    assert (
        compute_threat(world, SCENARIO, PLAYER).atrocity == 2 * TUNING.atrocity_threat
    )


def test_threat_is_capped_at_one_hundred() -> None:
    world = make_world()
    for _ in range(50):
        record_atrocity(world, PLAYER)

    assert compute_threat(world, SCENARIO, PLAYER).value == 100


def test_ledger_does_nothing_for_a_legacy_world() -> None:
    world = make_world()
    world.coalition_ruleset = 0
    before = world.factions[PLAYER].reputation

    record_conquest(world, SCENARIO, PLAYER, _region(world))
    record_atrocity(world, PLAYER)

    assert world.coalition.conquests == []
    assert world.coalition.atrocities == {}
    assert world.factions[PLAYER].reputation == before

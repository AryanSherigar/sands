from app.engine.overtures.selection import select_overture
from strategy_contracts.overtures import OvertureKind

from tests.engine.overtures.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
    scenario_with,
    war_world,
)

NEVER_EXHAUSTED = {"peace_offer_min_strain": 101, "peace_offer_max_will": 0}


def test_exhausted_npc_at_war_offers_peace() -> None:
    world = war_world()
    scenario = scenario_with(peace_offer_min_strain=0)

    assert select_overture(world, scenario) == (
        WRATHFUL_RIVAL,
        OvertureKind.PEACE_OFFER,
    )


def test_strong_npc_demands() -> None:
    world = war_world(attacker_score=60, defender_score=0)
    scenario = scenario_with(**NEVER_EXHAUSTED)

    assert select_overture(world, scenario) == (WRATHFUL_RIVAL, OvertureKind.DEMAND)


def test_long_even_war_prompts_a_call_for_talks() -> None:
    world = war_world()
    world.clock.turn += 3
    scenario = scenario_with(**NEVER_EXHAUSTED)

    assert select_overture(world, scenario) == (
        WRATHFUL_RIVAL,
        OvertureKind.CALL_FOR_TALKS,
    )


def test_young_even_war_selects_nothing() -> None:
    world = war_world()

    assert select_overture(world, scenario_with(**NEVER_EXHAUSTED)) is None


def test_cooldown_blocks_second_overture() -> None:
    world = war_world()
    world.overture_cooldowns[WRATHFUL_RIVAL] = world.clock.turn + 1

    assert select_overture(world, scenario_with(peace_offer_min_strain=0)) is None


def test_lowest_sorted_id_wins_when_two_qualify() -> None:
    world = war_world()
    add_war(world, attacker_id=CAUTIOUS_RIVAL, defender_id=PLAYER, war_id="war_2")
    chosen = select_overture(world, scenario_with(peace_offer_min_strain=0))

    assert chosen is not None
    assert chosen[0] == min(CAUTIOUS_RIVAL, WRATHFUL_RIVAL)


def test_leaderless_npc_never_approaches() -> None:
    world = war_world()
    world.factions[WRATHFUL_RIVAL].leader_id = None

    assert select_overture(world, scenario_with(peace_offer_min_strain=0)) is None


def test_ruleset_0_world_selects_nothing() -> None:
    world = war_world()
    world.overture_ruleset = 0

    assert select_overture(world, scenario_with(peace_offer_min_strain=0)) is None


def test_disabled_toggle_selects_nothing() -> None:
    world = war_world()
    scenario = scenario_with(peace_offer_min_strain=0)
    toggles = scenario.toggles.model_copy(update={"is_overtures_enabled": False})
    scenario = scenario.model_copy(update={"toggles": toggles})

    assert select_overture(world, scenario) is None


def test_peace_time_selects_nothing() -> None:
    assert select_overture(make_world(), SCENARIO) is None

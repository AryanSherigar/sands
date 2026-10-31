from app.engine.ai.catalog import legal_candidates
from app.engine.ai.generators.recon import scout_candidates
from app.models.orders import MapScoutOrder
from app.models.world_ai import AimState
from app.models.world_region import RegionIntel
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

TUNING = SCENARIO.tuning.ai


def _targets(world) -> list[str]:
    candidates = scout_candidates(world, SCENARIO, CAUTIOUS_RIVAL)
    assert all(isinstance(item.order, MapScoutOrder) for item in candidates)
    return [item.order.target_region_id for item in candidates]


def _intel(turn: int) -> RegionIntel:
    return RegionIntel(
        last_seen_turn=turn, owner_id=None, garrison_low=10, garrison_high=20
    )


def test_unknown_regions_next_to_sight_are_scouted_two_at_a_time() -> None:
    assert _targets(make_world()) == ["aldgate", "brennmoor"]


def test_attack_aim_scouts_around_the_target_first() -> None:
    world = make_world()
    world.aims[CAUTIOUS_RIVAL] = AimState(
        category=ScoreCategory.ATTACK,
        target_faction_id=WRATHFUL_RIVAL,
        chosen_turn=0,
        leader_id=world.factions[CAUTIOUS_RIVAL].leader_id,
        capital_held=True,
    )

    assert _targets(world) == ["dunwick", "aldgate"]


def test_recent_intel_is_not_scouted_again_but_stale_intel_is() -> None:
    world = make_world()
    world.clock.turn = 10
    world.factions[CAUTIOUS_RIVAL].intel["aldgate"] = _intel(turn=9)
    world.factions[CAUTIOUS_RIVAL].intel["brennmoor"] = _intel(
        turn=10 - TUNING.scout_stale_turns
    )

    assert _targets(world) == ["brennmoor", "dunwick"]


def test_scouts_are_legal_orders_and_category_expand() -> None:
    world = make_world()
    candidates = scout_candidates(world, SCENARIO, CAUTIOUS_RIVAL)

    assert {item.category for item in candidates} == {ScoreCategory.EXPAND}
    assert legal_candidates(world, SCENARIO, CAUTIOUS_RIVAL, candidates) == candidates

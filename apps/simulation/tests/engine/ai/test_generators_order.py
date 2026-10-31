from app.engine.ai.catalog import legal_candidates
from app.engine.ai.generators.order import uprising_candidates
from app.models.battle_command import ResolveUprisingCommand
from app.models.world_internal import UprisingResponse, UprisingState
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

TUNING = SCENARIO.tuning.ai


def _uprising(uprising_id: str, region: str, faction: str) -> UprisingState:
    return UprisingState(
        id=uprising_id,
        region_id=region,
        faction_id=faction,
        started_turn=0,
        trigger_unrest=80,
        income_penalty_percent=10,
        manpower_penalty_percent=10,
        supply_penalty_percent=10,
    )


def test_each_uprising_gets_three_responses_with_distinct_categories() -> None:
    world = make_world()
    world.uprisings.append(_uprising("up_1", "carrow_vale", CAUTIOUS_RIVAL))

    candidates = uprising_candidates(world, SCENARIO, CAUTIOUS_RIVAL)

    by_response = {item.order.response: item for item in candidates}
    assert set(by_response) == set(UprisingResponse)
    assert by_response[UprisingResponse.CONCESSIONS].category == ScoreCategory.BUILD
    assert by_response[UprisingResponse.RESTORE_ORDER].category == ScoreCategory.ATTACK
    assert by_response[UprisingResponse.NEGOTIATE].category == ScoreCategory.ALLY
    assert {item.base_score for item in candidates} == {TUNING.uprising_bonus}
    assert all(isinstance(item.order, ResolveUprisingCommand) for item in candidates)


def test_other_factions_uprisings_and_peace_give_nothing() -> None:
    world = make_world()
    assert uprising_candidates(world, SCENARIO, CAUTIOUS_RIVAL) == []

    world.uprisings.append(_uprising("up_2", "dunwick", WRATHFUL_RIVAL))
    assert uprising_candidates(world, SCENARIO, CAUTIOUS_RIVAL) == []


def test_uprising_responses_are_legal_orders() -> None:
    world = make_world()
    world.uprisings.append(_uprising("up_1", "carrow_vale", CAUTIOUS_RIVAL))
    candidates = uprising_candidates(world, SCENARIO, CAUTIOUS_RIVAL)

    assert legal_candidates(world, SCENARIO, CAUTIOUS_RIVAL, candidates) == candidates

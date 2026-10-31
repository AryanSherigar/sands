import pytest
from app.engine.campaign import begin_campaign
from app.engine.hashing import world_hash
from app.engine.replay import replay_history
from app.exceptions.world_exceptions import ReplayMismatchError
from app.models.battle_progress import OperationGuard
from app.models.replay import BeginCampaignReplayInput, ReplayStep, ReplayStepKind
from app.models.stance import StanceChoice, StanceSource
from app.models.world_character import LeaderState
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns

from tests.models.builders import PLAYTHROUGH_ID, make_world

SCENARIO = load_three_crowns()
AI_FACTION = "house_ashford"


def _world() -> WorldState:
    world = make_world()
    world.leaders = {
        "mira": LeaderState(id="mira", name="Mira", faction_id=AI_FACTION, age=40),
    }
    world.factions[AI_FACTION].leader_id = "mira"
    return world


def _choice() -> StanceChoice:
    return StanceChoice(
        leader_id="mira",
        faction_id=AI_FACTION,
        due_turn=1,
        option_id="expand",
        source=StanceSource.MODEL,
        reason_code="model_pick",
        input_hash="hash-1",
    )


def _step(
    before: WorldState, after: WorldState, stances: list[StanceChoice]
) -> ReplayStep:
    guard = OperationGuard(
        operation_id="begin", expected_world_version=1, expected_turn=0, expected_wave=0
    )
    return ReplayStep(
        playthrough_id=PLAYTHROUGH_ID,
        sequence=1,
        operation_id="begin",
        kind=ReplayStepKind.BEGIN_CAMPAIGN,
        input=BeginCampaignReplayInput(guard=guard, stances=stances),
        before_hash=world_hash(before),
        after_hash=world_hash(after),
        turn=0,
        wave=0,
    )


def _begun() -> tuple[WorldState, WorldState]:
    before = _world()
    result = begin_campaign(
        before.model_copy(deep=True), SCENARIO, recorded_stances={"mira": _choice()}
    )
    return before, result.world


def test_completing_a_turn_applies_the_recorded_stance() -> None:
    _, after = _begun()
    assert after.clock.turn == 1
    assert after.factions[AI_FACTION].stance.option_id == "expand"
    assert after.factions[AI_FACTION].stance.chosen_turn == 1


def test_replay_with_recorded_stances_matches_original_hash() -> None:
    before, after = _begun()
    result = replay_history(before, SCENARIO, [_step(before, after, [_choice()])])
    assert result.world_hash == world_hash(after)


def test_replay_without_the_stance_input_mismatches() -> None:
    before, after = _begun()
    with pytest.raises(ReplayMismatchError):
        replay_history(before, SCENARIO, [_step(before, after, [])])

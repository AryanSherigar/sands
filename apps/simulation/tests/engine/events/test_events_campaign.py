from app.engine.campaign import begin_campaign
from app.engine.hashing import world_hash
from app.engine.replay import replay_history
from app.models.battle_progress import OperationGuard
from app.models.replay import BeginCampaignReplayInput, ReplayStep, ReplayStepKind
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns
from tests.models.builders import PLAYTHROUGH_ID, make_world

HOME = "carrow_vale"
HIGH_UNREST = 70
FULL_FREQUENCY = 100


def _scenario():
    scenario = load_three_crowns()
    scenario.tuning.event_frequency_percent = FULL_FREQUENCY
    return scenario


def _world(is_enabled: bool) -> WorldState:
    world = make_world()
    world.events_ruleset = 1 if is_enabled else 0
    world.regions[HOME].unrest = HIGH_UNREST
    return world


def _step(before: WorldState, after: WorldState) -> ReplayStep:
    guard = OperationGuard(
        operation_id="begin", expected_world_version=1, expected_turn=0, expected_wave=0
    )
    return ReplayStep(
        playthrough_id=PLAYTHROUGH_ID,
        sequence=1,
        operation_id="begin",
        kind=ReplayStepKind.BEGIN_CAMPAIGN,
        input=BeginCampaignReplayInput(guard=guard, stances=[]),
        before_hash=world_hash(before),
        after_hash=world_hash(after),
        turn=0,
        wave=0,
    )


def test_a_real_turn_fires_a_queued_event_without_pausing() -> None:
    result = begin_campaign(_world(is_enabled=True), _scenario())
    world = result.world
    assert world.clock.turn == 1
    assert world.progress.pending_scene_id is None
    assert world.progress.waiting_reason is None
    fired = [event for event in result.events if event.kind == "event_fired"]
    assert fired
    assert all(event.seq > 0 for event in fired)
    assert world.pending_events
    assert {pending.subject_id for pending in world.pending_events} >= {HOME}


def test_old_worlds_without_the_ruleset_never_fire_events() -> None:
    result = begin_campaign(_world(is_enabled=False), _scenario())
    assert result.world.pending_events == []
    assert result.world.event_memories == []
    assert "event_memories" not in result.world.model_dump(mode="json")


def test_replay_reproduces_a_turn_that_fired_events() -> None:
    before = _world(is_enabled=True)
    after = begin_campaign(before.model_copy(deep=True), _scenario()).world
    replayed = replay_history(before, _scenario(), [_step(before, after)])
    assert replayed.world_hash == world_hash(after)

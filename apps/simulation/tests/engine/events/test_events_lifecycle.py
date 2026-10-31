from app.engine.campaign import begin_campaign
from app.engine.events.phase import EventsPhase
from app.engine.hashing import world_hash
from app.engine.phases import PhaseContext
from app.engine.replay import replay_history
from app.engine.rng import derive_rng
from app.models.battle_progress import OperationGuard
from app.models.replay import BeginCampaignReplayInput, ReplayStep, ReplayStepKind
from app.models.world_character import GovernorState
from app.models.world_event_memory import EventMemory
from app.models.world_state import WorldState
from strategy_contracts.examples import load_three_crowns
from tests.models.builders import PLAYTHROUGH_ID, make_world

HOME = "carrow_vale"
GOVERNOR = "gov_carrow"
TURN = 5
TIER_ONE_UNREST = 40
NEGLECT_UNREST = 10
NEGLECT_OPINION = -10
NEGLECT_SCAR = 30
CALM_TURNS = 3
FULL_FREQUENCY = 100


def _world(unrest: int = TIER_ONE_UNREST) -> WorldState:
    world = make_world()
    world.events_ruleset = 1
    world.clock.turn = TURN
    world.regions[HOME].unrest = unrest
    world.regions[HOME].governor_id = GOVERNOR
    world.governors[GOVERNOR] = GovernorState(
        id=GOVERNOR, name="Lord Harl", region_id=HOME, opinion_of_ruler=0
    )
    return world


def _run(world: WorldState, turn: int | None = None):
    scenario = load_three_crowns()
    scenario.tuning.event_frequency_percent = FULL_FREQUENCY
    if turn is not None:
        world.clock.turn = turn
    context = PhaseContext(
        scenario=scenario,
        orders=(),
        rng=derive_rng(42, world.clock.turn, "events"),
        resolved_outcomes={},
        recorded_answers={},
    )
    result = EventsPhase().run(world, context)
    return result.world, result.events


def _grievance(world: WorldState):
    return next(p for p in world.pending_events if p.template_id == "tax_grievance")


def test_event_is_not_neglected_before_its_deadline() -> None:
    world, _ = _run(_world())
    deadline = _grievance(world).deadline_turn
    after, events = _run(world, turn=deadline - 1)
    assert [e.kind for e in events if e.kind == "event_neglected"] == []
    assert any(p.template_id == "tax_grievance" for p in after.pending_events)


def test_unanswered_event_applies_its_neglect_outcome_at_the_deadline() -> None:
    world, _ = _run(_world())
    unrest_before = world.regions[HOME].unrest
    deadline = _grievance(world).deadline_turn
    after, events = _run(world, turn=deadline)
    neglected = [e for e in events if e.kind == "event_neglected"]
    assert len(neglected) == 1
    assert neglected[0].cause.summary_key == "events.tax_grievance.neglected"
    assert after.regions[HOME].unrest == unrest_before + NEGLECT_UNREST
    assert after.governors[GOVERNOR].opinion_of_ruler == NEGLECT_OPINION
    paths = {change.path for change in neglected[0].changes}
    assert paths == {f"regions.{HOME}.unrest", f"governors.{GOVERNOR}.opinion_of_ruler"}


def test_neglect_leaves_a_scar_and_removes_the_pending_event() -> None:
    world, _ = _run(_world())
    after, _ = _run(world, turn=_grievance(world).deadline_turn)
    memory = next(m for m in after.event_memories if m.template_id == "tax_grievance")
    assert memory.scar == NEGLECT_SCAR
    assert all(
        p.template_id != "tax_grievance" or p.created_turn > TURN
        for p in after.pending_events
    )


def test_neglect_can_push_the_problem_into_a_higher_tier() -> None:
    world, _ = _run(_world(unrest=TIER_ONE_UNREST + 15))
    first = _grievance(world)
    after, _ = _run(world, turn=first.deadline_turn)
    refired = [p for p in after.pending_events if p.template_id == "tax_grievance"]
    assert [p.tier for p in refired] == [2]
    assert refired[0].created_turn == first.deadline_turn


def test_a_scar_fades_each_turn() -> None:
    world = _world(unrest=0)
    world.event_memories.append(
        EventMemory(template_id="tax_grievance", subject_id=HOME, scar=NEGLECT_SCAR)
    )
    after, _ = _run(world)
    assert after.event_memories[0].scar == NEGLECT_SCAR - 1


def test_a_calm_tier_steps_down_one_level_after_enough_calm_turns() -> None:
    world = _world(unrest=0)
    world.event_memories.append(
        EventMemory(template_id="tax_grievance", subject_id=HOME, last_tier=2)
    )
    for _ in range(CALM_TURNS - 1):
        world, _ = _run(world)
    assert world.event_memories[0].last_tier == 2
    world, _ = _run(world)
    assert world.event_memories[0].last_tier == 1
    assert world.event_memories[0].calm_turns == 0


def test_trouble_returning_resets_the_calm_count() -> None:
    world = _world(unrest=0)
    world.event_memories.append(
        EventMemory(
            template_id="tax_grievance", subject_id=HOME, last_tier=1, calm_turns=2
        )
    )
    world.regions[HOME].unrest = TIER_ONE_UNREST
    after, _ = _run(world)
    memory = next(m for m in after.event_memories if m.template_id == "tax_grievance")
    assert memory.calm_turns == 0
    assert memory.last_tier == 1


def test_a_fully_calmed_memory_with_no_scar_is_forgotten() -> None:
    world = _world(unrest=0)
    world.event_memories.append(
        EventMemory(
            template_id="tax_grievance",
            subject_id=HOME,
            last_tier=1,
            calm_turns=CALM_TURNS - 1,
        )
    )
    after, _ = _run(world)
    assert after.event_memories == []


def test_forgotten_problem_fires_again_from_the_first_tier() -> None:
    world = _world(unrest=0)
    world.event_memories.append(
        EventMemory(
            template_id="tax_grievance",
            subject_id=HOME,
            last_tier=1,
            calm_turns=CALM_TURNS - 1,
        )
    )
    world, _ = _run(world)
    world.regions[HOME].unrest = TIER_ONE_UNREST
    after, _ = _run(world)
    assert [
        p.tier for p in after.pending_events if p.template_id == "tax_grievance"
    ] == [1]


def _guard(operation: str, turn: int) -> OperationGuard:
    return OperationGuard(
        operation_id=operation,
        expected_world_version=1,
        expected_turn=turn,
        expected_wave=0,
    )


def _step(
    sequence: int, turn: int, before: WorldState, after: WorldState
) -> ReplayStep:
    return ReplayStep(
        playthrough_id=PLAYTHROUGH_ID,
        sequence=sequence,
        operation_id=f"begin-{sequence}",
        kind=ReplayStepKind.BEGIN_CAMPAIGN,
        input=BeginCampaignReplayInput(guard=_guard(f"begin-{sequence}", turn)),
        before_hash=world_hash(before),
        after_hash=world_hash(after),
        turn=turn,
        wave=0,
    )


def test_a_real_rollover_neglects_and_replays_to_the_same_hash() -> None:
    scenario = load_three_crowns()
    scenario.tuning.event_frequency_percent = FULL_FREQUENCY
    start = make_world()
    start.events_ruleset = 1
    start.regions[HOME].unrest = 70
    first = begin_campaign(start.model_copy(deep=True), scenario)
    second = begin_campaign(first.world.model_copy(deep=True), scenario)
    assert any(e.kind == "event_neglected" for e in second.events)
    steps = [
        _step(1, 0, start, first.world),
        _step(2, 1, first.world, second.world),
    ]
    replayed = replay_history(start, scenario, steps)
    assert replayed.world_hash == world_hash(second.world)

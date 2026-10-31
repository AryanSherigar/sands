from uuid import UUID

import pytest
from app.engine.phases import PhaseContext, PhaseResult, ScenePause
from app.engine.pipeline import run_turn
from app.engine.promises.signing import sign_sworn_promise
from app.exceptions.world_exceptions import MissingPhaseError, PhaseEventMismatchError
from app.models.world_diplomacy import CommitmentStatus
from app.models.world_events import (
    PHASE_ORDER,
    EventCause,
    EventLogEntry,
    PhaseName,
    TurnStatus,
)
from app.models.world_state import CounterKind, WorldState
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.scene import ProseOnlyOutcome, SceneType
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm

from tests.models.builders import make_relation, make_world

SCENE_ID = UUID("44444444-4444-4444-4444-444444444444")


def _event(phase: PhaseName) -> EventLogEntry:
    return EventLogEntry(
        seq=0,
        turn=0,
        phase=phase,
        kind="test",
        cause=EventCause(summary_key="test"),
    )


class RecordingPhase:
    def __init__(self, name: PhaseName, log: list[PhaseName]) -> None:
        self.name = name
        self._log = log

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        self._log.append(self.name)
        return PhaseResult(world=world, events=[_event(self.name)])


class RollingPhase:
    name = PhaseName.ECONOMY

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        world.regions["ashford"].unrest = context.rng.roll(100)
        return PhaseResult(world=world)


class PausingPhase:
    name = PhaseName.BATTLES

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        outcome = context.resolved_outcomes.get(world.progress.pending_scene_id)
        if outcome is None:
            pause = ScenePause(SceneType.BATTLE_SPEECH, ("army_a",))
            return PhaseResult(world=world, pause=pause)
        world.regions["ashford"].unrest = 77
        return PhaseResult(world=world, events=[_event(self.name)])


class FailingPhase:
    name = PhaseName.MOVEMENT

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        world.regions["ashford"].unrest = 99
        raise RuntimeError("boom")


def _all_phases(log: list[PhaseName]) -> dict[PhaseName, RecordingPhase]:
    return {name: RecordingPhase(name, log) for name in PHASE_ORDER}


class NoopPhase:
    def __init__(self, name: PhaseName) -> None:
        self.name = name

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        return PhaseResult(world=world)


def _run(world: WorldState, phases: dict, outcomes: dict | None = None):
    complete = {name: NoopPhase(name) for name in PHASE_ORDER} | phases
    return run_turn(world, load_three_crowns(), [], complete, outcomes or {}, {})


def test_phases_run_in_rfc_order() -> None:
    log: list[PhaseName] = []
    result = _run(make_world(), _all_phases(log))
    assert log == list(PHASE_ORDER)
    assert result.status is TurnStatus.RESOLVED


def test_missing_phase_is_rejected_before_anything_runs() -> None:
    log: list[PhaseName] = []
    phases = _all_phases(log)
    del phases[PhaseName.SIEGES]
    with pytest.raises(MissingPhaseError):
        run_turn(make_world(), load_three_crowns(), [], phases, {}, {})
    assert log == []


def test_event_from_another_phase_is_rejected() -> None:
    class MislabelingPhase(NoopPhase):
        def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
            return PhaseResult(world=world, events=[_event(PhaseName.TIME)])

    with pytest.raises(PhaseEventMismatchError):
        _run(make_world(), {PhaseName.ECONOMY: MislabelingPhase(PhaseName.ECONOMY)})


def test_events_are_stamped_with_the_running_turn() -> None:
    world = make_world()
    world.clock.turn = 3
    result = _run(world, _all_phases([]))
    assert {event.turn for event in result.events} == {3}


def test_lists_are_sorted_after_each_phase() -> None:
    class UnsortedPhase(NoopPhase):
        def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
            world.relations = [
                make_relation("house_carrow", "house_dunwick"),
                make_relation("house_ashford", "house_carrow"),
            ]
            return PhaseResult(world=world)

    result = _run(
        make_world(), {PhaseName.DIPLOMACY: UnsortedPhase(PhaseName.DIPLOMACY)}
    )
    assert [(item.faction_a, item.faction_b) for item in result.world.relations] == [
        ("house_ashford", "house_carrow"),
        ("house_carrow", "house_dunwick"),
    ]


def test_each_phase_draws_from_its_own_stream() -> None:
    class DrawingPhase(NoopPhase):
        def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
            world.regions["ashford"].unrest = context.rng.roll(100)
            return PhaseResult(world=world)

    class ExtraDrawsPhase(NoopPhase):
        def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
            for _ in range(7):
                context.rng.next_u64()
            return PhaseResult(world=world)

    baseline = _run(make_world(), {PhaseName.ECONOMY: DrawingPhase(PhaseName.ECONOMY)})
    disturbed = _run(
        make_world(),
        {
            PhaseName.MOVEMENT: ExtraDrawsPhase(PhaseName.MOVEMENT),
            PhaseName.ECONOMY: DrawingPhase(PhaseName.ECONOMY),
        },
    )
    assert baseline.world_hash == disturbed.world_hash


def test_input_world_is_not_mutated() -> None:
    world = make_world()
    before = world.model_dump()
    _run(world, {PhaseName.ECONOMY: RollingPhase()})
    assert world.model_dump() == before


def test_events_are_numbered_from_one_when_counter_is_empty() -> None:
    result = _run(make_world(), _all_phases([]))
    assert [event.seq for event in result.events] == list(range(1, 11))


def test_completed_turn_evaluates_summary_triggers_after_event_stamping() -> None:
    class SummaryPhase(NoopPhase):
        def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
            player_id = next(
                faction.id for faction in world.factions.values() if faction.is_player
            )
            return PhaseResult(
                world=world,
                events=[
                    EventLogEntry(
                        seq=0,
                        turn=0,
                        phase=self.name,
                        kind="test_major",
                        is_major=True,
                        cause=EventCause(
                            summary_key="test_major", subject_ids=[player_id]
                        ),
                    )
                ],
            )

    world = make_world()
    world.summary_ruleset = 1
    result = _run(world, {PhaseName.ECONOMY: SummaryPhase(PhaseName.ECONOMY)})

    assert result.world.summary_requests[0].event_seqs == [1]
    assert result.world.summary_requests[0].trigger == "major_event"


def test_event_numbering_continues_from_stored_counter() -> None:
    world = make_world()
    world.counters[CounterKind.EVENT_SEQ] = 5
    phases = {name: RecordingPhase(name, []) for name in PHASE_ORDER[:2]}
    result = _run(world, phases)
    assert [event.seq for event in result.events] == [6, 7]
    assert result.world.counters[CounterKind.EVENT_SEQ] == 7


def test_runs_are_deterministic() -> None:
    first = _run(make_world(), {PhaseName.ECONOMY: RollingPhase()})
    second = _run(make_world(), {PhaseName.ECONOMY: RollingPhase()})
    assert first.world_hash == second.world_hash


def test_pause_stops_before_the_pausing_phase_applies() -> None:
    log: list[PhaseName] = []
    phases = _all_phases(log)
    phases[PhaseName.BATTLES] = PausingPhase()
    result = _run(make_world(), phases)
    assert result.status is TurnStatus.PAUSED
    assert result.pause == ScenePause(SceneType.BATTLE_SPEECH, ("army_a",))
    assert result.world.progress.phase is PhaseName.BATTLES
    assert result.world.clock.turn == 0
    assert result.world_hash is None
    assert [event.phase for event in result.events] == list(PHASE_ORDER[:3])


def test_resume_reruns_only_the_paused_phase_onward() -> None:
    log: list[PhaseName] = []
    phases = _all_phases(log)
    phases[PhaseName.BATTLES] = PausingPhase()
    paused = _run(make_world(), phases)
    log.clear()
    resumable = paused.world.model_copy(deep=True)
    resumable.progress.pending_scene_id = SCENE_ID
    result = _run(resumable, phases, {SCENE_ID: ProseOnlyOutcome()})
    assert result.status is TurnStatus.RESOLVED
    assert PhaseName.ORDERS not in log
    assert log[0] is PhaseName.SIEGES
    assert result.world.regions["ashford"].unrest == 77
    assert result.world.clock.turn == 1
    assert result.world.progress.phase is None


def test_failing_phase_propagates_and_leaves_input_untouched() -> None:
    world = make_world()
    before = world.model_dump()
    with pytest.raises(RuntimeError):
        _run(world, {PhaseName.MOVEMENT: FailingPhase()})
    assert world.model_dump() == before


class WarDeclaringPhase:
    name = PhaseName.DIPLOMACY

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        event = EventLogEntry(
            seq=0,
            turn=0,
            phase=self.name,
            kind="war_declared",
            cause=EventCause(
                summary_key="war_declared",
                subject_ids=["war_1", "house_ashford", "house_carrow"],
            ),
        )
        return PhaseResult(world=world, events=[event])


def _world_with_promise() -> WorldState:
    world = make_world()
    sign_sworn_promise(
        world,
        SwornPromiseTerm(
            promisor_id="house_ashford",
            beneficiary_id="house_carrow",
            promise=PromiseKind.NEVER_ATTACK_FACTION,
            duration_turns=5,
        ),
        None,
    )
    return world


def test_run_turn_applies_the_breach_from_a_stub_phase_event() -> None:
    result = _run(_world_with_promise(), {PhaseName.DIPLOMACY: WarDeclaringPhase()})

    assert result.world.commitments[0].status is CommitmentStatus.BREACHED
    kinds = [event.kind for event in result.events]
    assert kinds == ["war_declared", "sworn_promise_broken"]
    assert [event.seq for event in result.events] == [1, 2]


def test_breach_runs_are_deterministic() -> None:
    phases = {PhaseName.DIPLOMACY: WarDeclaringPhase()}
    first = _run(_world_with_promise(), phases)
    second = _run(_world_with_promise(), phases)

    assert first.world_hash == second.world_hash

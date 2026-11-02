from app.engine.phases import PhaseContext, PhaseResult
from app.engine.pipeline import run_turn
from app.models.world_events import PHASE_ORDER, PhaseName, TurnStatus
from app.models.world_state import WorldState

from tests.engine.judgments.builders import (
    CAPTIVE_ID,
    GOVERNOR_ID,
    judgment_scenario,
    judgment_world,
    uprising_event,
)


class NoopPhase:
    def __init__(self, name: PhaseName) -> None:
        self.name = name

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        return PhaseResult(world=world)


class UprisingPhase(NoopPhase):
    def __init__(self) -> None:
        super().__init__(PhaseName.INTERNAL)

    def run(self, world: WorldState, context: PhaseContext) -> PhaseResult:
        return PhaseResult(world=world, events=[uprising_event("uprising_crushed")])


def _roll(world: WorldState, scenario=None, uprising: bool = False):
    phases = {name: NoopPhase(name) for name in PHASE_ORDER}
    if uprising:
        phases[PhaseName.INTERNAL] = UprisingPhase()
    return run_turn(world, scenario or judgment_scenario(), [], phases, {}, {})


def test_a_rollover_with_a_held_captive_arms_a_judgment() -> None:
    result = _roll(judgment_world())
    assert result.status is TurnStatus.RESOLVED
    pending = result.world.progress.pending_judgment
    assert pending is not None
    assert pending.subject_id == CAPTIVE_ID
    assert result.world.progress.pending_scene_id is not None


def test_a_crushed_uprising_this_turn_arms_the_governor_judgment() -> None:
    world = judgment_world()
    world.prisoners = []
    result = _roll(world, uprising=True)
    assert result.world.progress.pending_judgment.subject_id == GOVERNOR_ID


def test_a_rollover_with_judgments_off_arms_nothing() -> None:
    result = _roll(judgment_world(), judgment_scenario(is_enabled=False))
    assert result.world.progress.pending_judgment is None
    assert result.world.progress.pending_scene_id is None

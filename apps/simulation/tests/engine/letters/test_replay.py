import pytest
from app.engine.hashing import world_hash
from app.engine.letters.arming import arm_letter
from app.engine.letters.closing import close_letter
from app.engine.letters.constants import LETTER_WARMER
from app.engine.replay import replay_history
from app.exceptions.world_exceptions import ReplayMismatchError
from app.models.battle_progress import OperationGuard
from app.models.replay import ReplayStep, ReplayStepKind, ResolveSceneReplayInput
from strategy_contracts.scene import ChoiceOutcome, SceneType

from tests.engine.letters.builders import letter_scenario, letter_world, set_opinion
from tests.models.builders import PLAYTHROUGH_ID

GUARD = OperationGuard(
    operation_id="op-close", expected_world_version=1, expected_turn=4, expected_wave=0
)


def _steps(option_id: str = LETTER_WARMER):
    scenario = letter_scenario()
    start = letter_world()
    set_opinion(start, 2)
    start.playthrough_id = PLAYTHROUGH_ID
    arm_letter(start, scenario)
    scene_id = start.progress.pending_scene_id
    outcome = ChoiceOutcome(option_id=option_id)
    closed, _ = close_letter(start, scenario, scene_id, outcome)
    step = ReplayStep(
        playthrough_id=PLAYTHROUGH_ID,
        sequence=1,
        operation_id="op-close",
        kind=ReplayStepKind.RESOLVE_SCENE,
        input=ResolveSceneReplayInput(
            guard=GUARD,
            scene_id=scene_id,
            scene_type=SceneType.LETTER,
            outcome=outcome,
        ),
        before_hash=world_hash(start),
        after_hash=world_hash(closed),
        turn=4,
        wave=0,
    )
    return scenario, start, step, closed


def test_a_closed_letter_replays_to_the_live_world_hash() -> None:
    scenario, start, step, closed = _steps()
    result = replay_history(start, scenario, [step])
    assert result.world_hash == world_hash(closed)
    assert result.world.leaders == closed.leaders


def test_a_tampered_letter_outcome_is_caught_by_the_replay_hash() -> None:
    scenario, start, step, _ = _steps()
    other = step.input.model_copy(
        update={"outcome": ChoiceOutcome(option_id="letter_cooler")}
    )
    with pytest.raises(ReplayMismatchError):
        replay_history(start, scenario, [step.model_copy(update={"input": other})])

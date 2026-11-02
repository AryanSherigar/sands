import pytest
from app.engine.hashing import world_hash
from app.engine.judgments.closing import close_judgment
from app.engine.replay import replay_history
from app.exceptions.world_exceptions import ReplayMismatchError
from app.models.battle_progress import OperationGuard
from app.models.replay import ReplayStep, ReplayStepKind, ResolveSceneReplayInput
from strategy_contracts.judgment import JudgmentNuance, JudgmentOutcome, JudgmentVerdict
from strategy_contracts.scene import SceneType

from tests.engine.judgments.builders import (
    TURN,
    arm_manually,
    captive_pending,
    judgment_scenario,
    judgment_world,
)
from tests.models.builders import PLAYTHROUGH_ID

GUARD = OperationGuard(
    operation_id="op-close",
    expected_world_version=1,
    expected_turn=TURN,
    expected_wave=0,
)
OUTCOME = JudgmentOutcome(
    verdict=JudgmentVerdict.EXECUTE, nuance=JudgmentNuance.PUBLICLY
)


def _steps(outcome: JudgmentOutcome = OUTCOME):
    scenario = judgment_scenario()
    start = judgment_world()
    start.playthrough_id = PLAYTHROUGH_ID
    scene_id = arm_manually(start, captive_pending())
    closed, _ = close_judgment(start, scenario, scene_id, outcome)
    step = ReplayStep(
        playthrough_id=PLAYTHROUGH_ID,
        sequence=1,
        operation_id="op-close",
        kind=ReplayStepKind.RESOLVE_SCENE,
        input=ResolveSceneReplayInput(
            guard=GUARD,
            scene_id=scene_id,
            scene_type=SceneType.JUDGMENT,
            outcome=outcome,
        ),
        before_hash=world_hash(start),
        after_hash=world_hash(closed),
        turn=TURN,
        wave=0,
    )
    return scenario, start, step, closed


def test_a_closed_judgment_replays_to_the_live_world_hash() -> None:
    scenario, start, step, closed = _steps()
    result = replay_history(start, scenario, [step])
    assert result.world_hash == world_hash(closed)
    assert result.world.player_profile.cruelty_acts == 1
    assert result.world.prisoners == []


def test_a_tampered_judgment_outcome_is_caught_by_the_replay_hash() -> None:
    scenario, start, step, _ = _steps()
    other = step.input.model_copy(
        update={"outcome": JudgmentOutcome(verdict=JudgmentVerdict.RELEASE)}
    )
    with pytest.raises(ReplayMismatchError):
        replay_history(start, scenario, [step.model_copy(update={"input": other})])

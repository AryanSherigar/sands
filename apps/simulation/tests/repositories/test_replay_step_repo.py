import pytest
from app.models.battle_progress import OperationGuard
from app.models.replay import (
    BeginCampaignReplayInput,
    ReplayStep,
    ReplayStepKind,
)
from app.repositories import replay_step_repo
from psycopg.errors import UniqueViolation

from tests.repositories.helpers import seed_playthrough


def _step(playthrough_id, sequence: int, operation_id: str) -> ReplayStep:
    return ReplayStep(
        playthrough_id=playthrough_id,
        sequence=sequence,
        operation_id=operation_id,
        kind=ReplayStepKind.BEGIN_CAMPAIGN,
        input=BeginCampaignReplayInput(
            guard=OperationGuard(
                operation_id=operation_id,
                expected_world_version=sequence,
                expected_turn=0,
                expected_wave=0,
            )
        ),
        before_hash=f"before-{sequence}",
        after_hash=f"after-{sequence}",
        turn=0,
        wave=0,
    )


async def test_list_replay_steps_returns_sequence_order(db_connection) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    await replay_step_repo.insert_step(db_connection, _step(playthrough_id, 2, "two"))
    await replay_step_repo.insert_step(db_connection, _step(playthrough_id, 1, "one"))
    rows = await replay_step_repo.list_steps(db_connection, playthrough_id)
    assert [row.sequence for row in rows] == [1, 2]


async def test_replay_step_rejects_duplicate_operation(db_connection) -> None:
    playthrough_id = await seed_playthrough(db_connection)
    await replay_step_repo.insert_step(db_connection, _step(playthrough_id, 1, "one"))
    with pytest.raises(UniqueViolation):
        await replay_step_repo.insert_step(
            db_connection, _step(playthrough_id, 2, "one")
        )


async def test_replay_step_accepts_the_resolve_scene_kind(db_connection) -> None:
    from uuid import UUID

    from app.models.replay import ResolveSceneReplayInput
    from strategy_contracts.scene import ChoiceOutcome, SceneType

    playthrough_id = await seed_playthrough(db_connection)
    step = _step(playthrough_id, 1, "close-letter").model_copy(
        update={
            "kind": ReplayStepKind.RESOLVE_SCENE,
            "input": ResolveSceneReplayInput(
                guard=OperationGuard(
                    operation_id="close-letter",
                    expected_world_version=1,
                    expected_turn=0,
                    expected_wave=0,
                ),
                scene_id=UUID(int=1),
                scene_type=SceneType.LETTER,
                outcome=ChoiceOutcome(option_id="letter_no_effect"),
            ),
        }
    )

    await replay_step_repo.insert_step(db_connection, step)

    rows = await replay_step_repo.list_steps(db_connection, playthrough_id)
    assert rows[0].kind is ReplayStepKind.RESOLVE_SCENE

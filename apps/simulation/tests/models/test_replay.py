from uuid import uuid4

import pytest
from app.models.battle_progress import OperationGuard
from app.models.replay import (
    BeginCampaignReplayInput,
    ReplayStep,
    ReplayStepKind,
    ordered_replay_steps,
)


def _step(sequence: int) -> ReplayStep:
    return ReplayStep(
        playthrough_id=uuid4(),
        sequence=sequence,
        operation_id=f"operation-{sequence}",
        kind=ReplayStepKind.BEGIN_CAMPAIGN,
        input=BeginCampaignReplayInput(
            guard=OperationGuard(
                operation_id=f"operation-{sequence}",
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


def test_ordered_replay_steps_sorts_a_complete_sequence() -> None:
    assert [step.sequence for step in ordered_replay_steps([_step(2), _step(1)])] == [
        1,
        2,
    ]


def test_ordered_replay_steps_rejects_a_gap() -> None:
    with pytest.raises(ValueError, match="gap"):
        ordered_replay_steps([_step(1), _step(3)])

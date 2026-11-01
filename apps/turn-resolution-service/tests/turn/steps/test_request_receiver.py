"""Unit tests for request_receiver.py, with repositories mocked."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.exceptions.turn_exceptions import (
    CheckOwnershipError,
    CheckResolutionMismatchError,
    CheckResolutionRequiredError,
    MinigameResultMismatchError,
    ParticipantAccessDeniedError,
    ParticipantNotFoundError,
    PlaythroughNotActiveError,
    StrategyTurnUnsupportedError,
    TurnOrderError,
)
from app.models.auth import CurrentUser
from app.models.turn import TurnRequestInput
from app.turn.steps.request_receiver import receive_request
from pydantic import ValidationError


def _participant(
    participant_id: uuid.UUID, position: int, user_id: uuid.UUID | None = None
) -> SimpleNamespace:
    return SimpleNamespace(
        participant_id=participant_id,
        turn_order_position=position,
        user_id=user_id or uuid.uuid4(),
    )


async def test_solo_turn_passes_validation() -> None:
    playthrough_id = uuid.uuid4()
    participant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active", turn_count=0
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(participant_id, 1, user_id=user_id)
    ]

    turn_request = await receive_request(
        TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=playthrough_id,
            participant_id=participant_id,
            action_text="look",
        ),
        playthrough_repo,
        participant_repo,
        CurrentUser(user_id=user_id, token_version=1),
    )

    assert turn_request.turn_count == 0


async def test_strategy_turn_is_rejected_before_participant_lookup() -> None:
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active", turn_count=0, scenario_snapshot={"mode": "strategy"}
    )
    participant_repo = AsyncMock()

    with pytest.raises(StrategyTurnUnsupportedError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=uuid.uuid4(),
                participant_id=uuid.uuid4(),
                action_text="advance",
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=uuid.uuid4(), token_version=1),
        )

    participant_repo.list_by_playthrough.assert_not_awaited()


async def test_inactive_playthrough_raises() -> None:
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="completed", turn_count=5
    )
    participant_repo = AsyncMock()

    with pytest.raises(PlaythroughNotActiveError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=uuid.uuid4(),
                participant_id=uuid.uuid4(),
                action_text="look",
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=uuid.uuid4(), token_version=1),
        )


async def test_unknown_participant_raises() -> None:
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active", turn_count=0
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [_participant(uuid.uuid4(), 1)]

    with pytest.raises(ParticipantNotFoundError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=uuid.uuid4(),
                participant_id=uuid.uuid4(),
                action_text="look",
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=uuid.uuid4(), token_version=1),
        )


async def test_participant_user_mismatch_raises_access_denied() -> None:
    playthrough_id = uuid.uuid4()
    participant_id = uuid.uuid4()
    owner_user_id = uuid.uuid4()
    attacker_user_id = uuid.uuid4()

    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active", turn_count=0
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(participant_id, 1, user_id=owner_user_id)
    ]

    with pytest.raises(ParticipantAccessDeniedError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=playthrough_id,
                participant_id=participant_id,
                action_text="look",
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=attacker_user_id, token_version=1),
        )


async def test_unauthorized_user_cannot_leak_minigame_gating() -> None:
    playthrough_id = uuid.uuid4()
    participant_id = uuid.uuid4()
    owner_user_id = uuid.uuid4()
    attacker_user_id = uuid.uuid4()

    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active",
        turn_count=0,
        state={"_pending_minigame": {"minigame_id": "mg-dodge"}},
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(participant_id, 1, user_id=owner_user_id)
    ]

    with pytest.raises(ParticipantAccessDeniedError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=playthrough_id,
                participant_id=participant_id,
                action_text="look",
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=attacker_user_id, token_version=1),
        )


async def test_result_requires_matching_server_issued_attempt_id() -> None:
    playthrough_id = uuid.uuid4()
    participant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active",
        turn_count=0,
        state={"_pending_minigame": {"minigame_id": "mg-dodge", "attempt_id": "a-1"}},
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(participant_id, 1, user_id=user_id)
    ]

    with pytest.raises(MinigameResultMismatchError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=playthrough_id,
                participant_id=participant_id,
                action_text="result",
                action_kind="minigame_result",
                minigame_result={
                    "minigame_id": "mg-dodge",
                    "outcome_tag": "win",
                    "attempt_id": "stale",
                },
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=user_id, token_version=1),
        )


def test_minigame_result_rejects_forged_outcome_and_boolean_score() -> None:
    common = {
        "playthrough_id": uuid.uuid4(),
        "participant_id": uuid.uuid4(),
        "action_text": "result",
        "action_kind": "minigame_result",
        "minigame_result": {"minigame_id": "mg-dodge"},
    }
    with pytest.raises(ValidationError):
        TurnRequestInput.model_validate(
            {
                **common,
                "minigame_result": {
                    "minigame_id": "mg-dodge",
                    "outcome_tag": "forged",
                },
            }
        )
    with pytest.raises(ValidationError):
        TurnRequestInput.model_validate(
            {
                **common,
                "minigame_result": {
                    "minigame_id": "mg-dodge",
                    "outcome_tag": "win",
                    "score": True,
                },
            }
        )


async def test_multiplayer_out_of_turn_raises() -> None:
    acting_id = uuid.uuid4()
    user_id = uuid.uuid4()
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active", turn_count=0
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(uuid.uuid4(), 1),
        _participant(acting_id, 2, user_id=user_id),
    ]

    with pytest.raises(TurnOrderError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=uuid.uuid4(),
                participant_id=acting_id,
                action_text="look",
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=user_id, token_version=1),
        )


async def test_multiplayer_correct_turn_passes() -> None:
    first_id, second_id = uuid.uuid4(), uuid.uuid4()
    first_user_id = uuid.uuid4()
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active", turn_count=0
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(first_id, 1, user_id=first_user_id),
        _participant(second_id, 2),
    ]

    turn_request = await receive_request(
        TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=uuid.uuid4(),
            participant_id=first_id,
            action_text="look",
        ),
        playthrough_repo,
        participant_repo,
        CurrentUser(user_id=first_user_id, token_version=1),
    )

    assert turn_request.participant_id == first_id


async def test_narrative_action_blocked_while_check_pending() -> None:
    participant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active",
        turn_count=0,
        state={"_pending_check": {"check_id": "check-1"}},
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(participant_id, 1, user_id=user_id)
    ]

    with pytest.raises(CheckResolutionRequiredError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=uuid.uuid4(),
                participant_id=participant_id,
                action_text="look",
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=user_id, token_version=1),
        )


async def test_check_resolution_requires_pending_check() -> None:
    participant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active", turn_count=0, state={}
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(participant_id, 1, user_id=user_id)
    ]

    with pytest.raises(CheckResolutionMismatchError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=uuid.uuid4(),
                participant_id=participant_id,
                action_text="result",
                action_kind="check_resolution",
                check_resolution={"check_id": "check-1", "resolution": "attempt"},
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=user_id, token_version=1),
        )


async def test_check_resolution_requires_matching_check_id() -> None:
    participant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active",
        turn_count=0,
        state={
            "_pending_check": {
                "check_id": "check-1",
                "proposing_participant_id": str(participant_id),
            }
        },
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(participant_id, 1, user_id=user_id)
    ]

    with pytest.raises(CheckResolutionMismatchError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=uuid.uuid4(),
                participant_id=participant_id,
                action_text="result",
                action_kind="check_resolution",
                check_resolution={"check_id": "stale-check", "resolution": "attempt"},
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=user_id, token_version=1),
        )


async def test_check_resolution_requires_owning_participant() -> None:
    """Only the participant who proposed the check may resolve it — this is
    stricter than minigame_result, which has no such ownership check."""
    proposing_participant_id = uuid.uuid4()
    other_participant_id = uuid.uuid4()
    other_user_id = uuid.uuid4()
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active",
        turn_count=0,
        state={
            "_pending_check": {
                "check_id": "check-1",
                "proposing_participant_id": str(proposing_participant_id),
            }
        },
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(proposing_participant_id, 1),
        _participant(other_participant_id, 2, user_id=other_user_id),
    ]

    with pytest.raises(CheckOwnershipError):
        await receive_request(
            TurnRequestInput(
                client_action_id=uuid.uuid4(),
                playthrough_id=uuid.uuid4(),
                participant_id=other_participant_id,
                action_text="result",
                action_kind="check_resolution",
                check_resolution={"check_id": "check-1", "resolution": "attempt"},
            ),
            playthrough_repo,
            participant_repo,
            CurrentUser(user_id=other_user_id, token_version=1),
        )


async def test_check_resolution_bypasses_turn_order_for_the_owning_participant() -> (
    None
):
    """turn_count=0 means the rotation formula expects participant at index
    0 (turn_order_position=1) next, but the check's owner is the OTHER
    participant — check_resolution must not raise TurnOrderError for them."""
    first_id, second_id = uuid.uuid4(), uuid.uuid4()
    second_user_id = uuid.uuid4()
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active",
        turn_count=0,
        state={
            "_pending_check": {
                "check_id": "check-1",
                "proposing_participant_id": str(second_id),
            }
        },
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(first_id, 1),
        _participant(second_id, 2, user_id=second_user_id),
    ]

    turn_request = await receive_request(
        TurnRequestInput(
            client_action_id=uuid.uuid4(),
            playthrough_id=uuid.uuid4(),
            participant_id=second_id,
            action_text="result",
            action_kind="check_resolution",
            check_resolution={"check_id": "check-1", "resolution": "attempt"},
        ),
        playthrough_repo,
        participant_repo,
        CurrentUser(user_id=second_user_id, token_version=1),
    )

    assert turn_request.participant_id == second_id


# --- find_completed_turn: replay lookup -------------------------------------------------


def _turn_log(
    participant_id: uuid.UUID | None, playthrough_id: uuid.UUID
) -> SimpleNamespace:
    return SimpleNamespace(
        participant_id=participant_id,
        playthrough_id=playthrough_id,
        turn_number=1,
        narration_text="stored",
    )


def _replay_fixture(owner_user_id: uuid.UUID):
    playthrough_id, participant_id = uuid.uuid4(), uuid.uuid4()
    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=playthrough_id,
        participant_id=participant_id,
        action_text="look",
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        _participant(participant_id, 1, user_id=owner_user_id)
    ]
    turn_log_repo = AsyncMock()
    return turn_input, participant_repo, turn_log_repo


async def test_find_completed_turn_returns_none_for_a_new_action() -> None:
    from app.turn.steps.request_receiver import find_completed_turn

    user_id = uuid.uuid4()
    turn_input, participant_repo, turn_log_repo = _replay_fixture(user_id)
    turn_log_repo.get_by_client_action_id.return_value = None

    result = await find_completed_turn(
        turn_input,
        turn_log_repo,
        participant_repo,
        CurrentUser(user_id=user_id, token_version=1),
    )

    assert result is None
    participant_repo.list_by_playthrough.assert_not_awaited()
    turn_log_repo.get_by_client_action_id.assert_awaited_once_with(
        turn_input.playthrough_id, turn_input.client_action_id
    )


async def test_find_completed_turn_returns_the_stored_turn_for_its_owner() -> None:
    from app.turn.steps.request_receiver import find_completed_turn

    user_id = uuid.uuid4()
    turn_input, participant_repo, turn_log_repo = _replay_fixture(user_id)
    stored = _turn_log(turn_input.participant_id, turn_input.playthrough_id)
    turn_log_repo.get_by_client_action_id.return_value = stored

    result = await find_completed_turn(
        turn_input,
        turn_log_repo,
        participant_repo,
        CurrentUser(user_id=user_id, token_version=1),
    )

    assert result is stored


async def test_find_completed_turn_never_returns_another_users_turn() -> None:
    from app.turn.steps.request_receiver import find_completed_turn

    owner_id, attacker_id = uuid.uuid4(), uuid.uuid4()
    turn_input, participant_repo, turn_log_repo = _replay_fixture(owner_id)
    turn_log_repo.get_by_client_action_id.return_value = _turn_log(
        turn_input.participant_id, turn_input.playthrough_id
    )

    with pytest.raises(ParticipantAccessDeniedError):
        await find_completed_turn(
            turn_input,
            turn_log_repo,
            participant_repo,
            CurrentUser(user_id=attacker_id, token_version=1),
        )


async def test_find_completed_turn_rejects_a_turn_that_belongs_to_another_participant() -> (
    None
):
    from app.turn.steps.request_receiver import find_completed_turn

    user_id = uuid.uuid4()
    turn_input, participant_repo, turn_log_repo = _replay_fixture(user_id)
    turn_log_repo.get_by_client_action_id.return_value = _turn_log(
        uuid.uuid4(), turn_input.playthrough_id
    )

    with pytest.raises(ParticipantAccessDeniedError):
        await find_completed_turn(
            turn_input,
            turn_log_repo,
            participant_repo,
            CurrentUser(user_id=user_id, token_version=1),
        )


async def test_find_completed_turn_unknown_participant_raises_not_found() -> None:
    from app.turn.steps.request_receiver import find_completed_turn

    user_id = uuid.uuid4()
    turn_input, participant_repo, turn_log_repo = _replay_fixture(user_id)
    participant_repo.list_by_playthrough.return_value = []
    turn_log_repo.get_by_client_action_id.return_value = _turn_log(
        turn_input.participant_id, turn_input.playthrough_id
    )

    with pytest.raises(ParticipantNotFoundError):
        await find_completed_turn(
            turn_input,
            turn_log_repo,
            participant_repo,
            CurrentUser(user_id=user_id, token_version=1),
        )

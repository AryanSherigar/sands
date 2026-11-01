"""request_receiver caps a narrative action and leaves other kinds alone."""

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from app.config import settings
from app.models.auth import CurrentUser
from app.models.check_event import CheckResolutionInput
from app.models.turn import TurnRequest, TurnRequestInput
from app.turn.steps.request_receiver import receive_request

PENDING_CHECK_ID = str(uuid.uuid4())


@pytest.fixture
def small_cap(monkeypatch) -> int:
    monkeypatch.setattr(settings, "turn_action_max_chars", 20)
    return 20


async def _receive(has_pending_check: bool = False, **overrides) -> TurnRequest:
    participant_id, user_id = uuid.uuid4(), uuid.uuid4()
    state: dict[str, object] = {}
    if has_pending_check:
        state["_pending_check"] = {
            "check_id": PENDING_CHECK_ID,
            "kind": "dice",
            "proposing_participant_id": str(participant_id),
        }
    playthrough_repo = AsyncMock()
    playthrough_repo.get_by_id.return_value = SimpleNamespace(
        status="active", turn_count=0, state=state
    )
    participant_repo = AsyncMock()
    participant_repo.list_by_playthrough.return_value = [
        SimpleNamespace(
            participant_id=participant_id, turn_order_position=1, user_id=user_id
        )
    ]
    turn_input = TurnRequestInput(
        client_action_id=uuid.uuid4(),
        playthrough_id=uuid.uuid4(),
        participant_id=participant_id,
        **overrides,
    )
    return await receive_request(
        turn_input,
        playthrough_repo,
        participant_repo,
        CurrentUser(user_id=user_id, token_version=1),
    )


async def test_over_cap_narrative_action_is_cut_and_flagged(small_cap) -> None:
    turn_request = await _receive(action_text="x" * 50)

    assert turn_request.action_text == "x" * small_cap
    assert turn_request.input_truncation is not None
    assert turn_request.input_truncation.original_length == 50
    assert turn_request.input_truncation.max_length == small_cap


async def test_under_cap_narrative_action_has_no_truncation(small_cap) -> None:
    turn_request = await _receive(action_text="  look around  ")

    assert turn_request.action_text == "look around"
    assert turn_request.input_truncation is None


async def test_other_action_kinds_are_not_capped(small_cap) -> None:
    turn_request = await _receive(
        has_pending_check=True,
        action_text="y" * 50,
        action_kind="check_resolution",
        check_resolution=CheckResolutionInput(
            check_id=PENDING_CHECK_ID, resolution="attempt"
        ),
    )

    assert turn_request.action_text == "y" * 50
    assert turn_request.input_truncation is None

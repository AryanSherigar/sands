import structlog
from app.config import Settings
from app.models.stance import StanceSource
from app.services.stance_service import create_stance_candidate
from tests.services.stance_fixtures import (
    PRIVATE_DESCRIPTION,
    FakeStanceClient,
    ready_settings,
    stance_request,
)


async def test_valid_answer_is_marked_model() -> None:
    client = FakeStanceClient("expand")
    choice = await create_stance_candidate(stance_request(), ready_settings(), client)
    assert (choice.option_id, choice.source, choice.reason_code) == (
        "expand",
        StanceSource.MODEL,
        "model_pick",
    )
    assert choice.input_hash == "hash-1"
    assert (choice.leader_id, choice.due_turn) == ("mira", 1)


async def test_off_menu_answer_falls_back_with_reason_code() -> None:
    client = FakeStanceClient("conquer")
    choice = await create_stance_candidate(stance_request(), ready_settings(), client)
    assert (choice.option_id, choice.source, choice.reason_code) == (
        "turtle",
        StanceSource.FALLBACK,
        "off_menu",
    )


async def test_provider_timeout_falls_back() -> None:
    client = FakeStanceClient(error=TimeoutError())
    choice = await create_stance_candidate(stance_request(), ready_settings(), client)
    assert (choice.source, choice.reason_code) == (
        StanceSource.FALLBACK,
        "provider_error",
    )


async def test_malformed_provider_answer_falls_back() -> None:
    client = FakeStanceClient(error=ValueError("bad body"))
    choice = await create_stance_candidate(stance_request(), ready_settings(), client)
    assert choice.reason_code == "provider_error"


async def test_disabled_provider_is_never_called() -> None:
    client = FakeStanceClient("expand")
    choice = await create_stance_candidate(stance_request(), Settings(), client)
    assert client.calls == 0
    assert (choice.source, choice.reason_code) == (
        StanceSource.FALLBACK,
        "provider_disabled",
    )


async def test_no_prompt_text_in_logs() -> None:
    client = FakeStanceClient(error=TimeoutError())
    with structlog.testing.capture_logs() as logs:
        await create_stance_candidate(stance_request(), ready_settings(), client)
    assert logs
    assert PRIVATE_DESCRIPTION not in str(logs)
    assert "Mira" not in str(logs)

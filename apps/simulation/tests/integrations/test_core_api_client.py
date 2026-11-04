import json
from uuid import uuid4

import httpx
import pytest
import respx
from app.config import get_settings
from app.integrations.core_api_client import (
    HEADER_INTERNAL_SERVICE_TOKEN,
    OUTCOME_TEXT_MAX_CHARS,
    close_core_api_client,
    sync_outcome_text,
    sync_turn_count,
)


@pytest.fixture(autouse=True)
async def reset_client() -> None:
    await close_core_api_client()
    yield
    await close_core_api_client()


@pytest.mark.asyncio
@respx.mock
async def test_sync_turn_count_sends_expected_request() -> None:
    settings = get_settings()
    playthrough_id = uuid4()
    url = f"{settings.core_api_url}/internal/v1/playthroughs/{playthrough_id}/turn"

    route = respx.patch(url).respond(
        status_code=200,
        json={
            "playthrough_id": str(playthrough_id),
            "turn_count": 5,
            "status": "active",
        },
    )

    await sync_turn_count(playthrough_id, 5, is_ended=False)

    assert route.called
    request = route.calls.last.request
    assert (
        request.headers[HEADER_INTERNAL_SERVICE_TOKEN]
        == settings.internal_service_token
    )
    payload = json.loads(request.content)
    assert payload == {"turn_count": 5, "is_ended": False}


@pytest.mark.asyncio
@respx.mock
async def test_sync_turn_count_includes_is_ended() -> None:
    settings = get_settings()
    playthrough_id = uuid4()
    url = f"{settings.core_api_url}/internal/v1/playthroughs/{playthrough_id}/turn"

    route = respx.patch(url).respond(
        status_code=200,
        json={
            "playthrough_id": str(playthrough_id),
            "turn_count": 12,
            "status": "completed",
        },
    )

    await sync_turn_count(playthrough_id, 12, is_ended=True)

    assert route.called
    payload = json.loads(route.calls.last.request.content)
    assert payload == {"turn_count": 12, "is_ended": True}


@pytest.mark.asyncio
@respx.mock
async def test_sync_turn_count_swallows_http_error_status() -> None:
    settings = get_settings()
    playthrough_id = uuid4()
    url = f"{settings.core_api_url}/internal/v1/playthroughs/{playthrough_id}/turn"

    respx.patch(url).respond(status_code=500)

    # Must not raise
    await sync_turn_count(playthrough_id, 3, is_ended=False)


@pytest.mark.asyncio
@respx.mock
async def test_sync_turn_count_swallows_network_exception() -> None:
    settings = get_settings()
    playthrough_id = uuid4()
    url = f"{settings.core_api_url}/internal/v1/playthroughs/{playthrough_id}/turn"

    respx.patch(url).side_effect = httpx.ConnectError("Connection refused")

    # Must not raise
    await sync_turn_count(playthrough_id, 3, is_ended=False)


@pytest.mark.asyncio
@respx.mock
async def test_sync_turn_count_swallows_timeout() -> None:
    settings = get_settings()
    playthrough_id = uuid4()
    url = f"{settings.core_api_url}/internal/v1/playthroughs/{playthrough_id}/turn"

    respx.patch(url).side_effect = httpx.ReadTimeout("Timeout")

    # Must not raise
    await sync_turn_count(playthrough_id, 3, is_ended=False)


@pytest.mark.asyncio
@respx.mock
async def test_sync_turn_count_swallows_client_error_404_and_422() -> None:
    settings = get_settings()
    playthrough_id = uuid4()
    url = f"{settings.core_api_url}/internal/v1/playthroughs/{playthrough_id}/turn"

    respx.patch(url).respond(status_code=404)
    await sync_turn_count(playthrough_id, 3, is_ended=False)

    respx.patch(url).respond(status_code=422)
    await sync_turn_count(playthrough_id, 3, is_ended=False)


@pytest.mark.asyncio
@respx.mock
async def test_sync_turn_count_reuses_client_instance() -> None:
    settings = get_settings()
    playthrough_id = uuid4()
    url = f"{settings.core_api_url}/internal/v1/playthroughs/{playthrough_id}/turn"

    route = respx.patch(url).respond(status_code=200)

    from app.integrations import core_api_client

    await sync_turn_count(playthrough_id, 1, is_ended=False)
    client_one = core_api_client._client
    assert client_one is not None

    await sync_turn_count(playthrough_id, 2, is_ended=False)
    client_two = core_api_client._client
    assert client_one is client_two
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_ended_sync_carries_the_outcome_and_a_running_sync_does_not() -> None:
    settings = get_settings()
    playthrough_id = uuid4()
    url = f"{settings.core_api_url}/internal/v1/playthroughs/{playthrough_id}/turn"
    route = respx.patch(url).respond(status_code=200)

    await sync_turn_count(
        playthrough_id, 9, True, outcome_tag="win", outcome_title="Victory Conquest"
    )
    await sync_turn_count(
        playthrough_id, 4, False, outcome_tag="win", outcome_title="ignored"
    )

    import json

    ended, running = (json.loads(call.request.content) for call in route.calls)
    assert ended == {
        "turn_count": 9,
        "is_ended": True,
        "ended_outcome_tag": "win",
        "ended_outcome_title": "Victory Conquest",
    }
    assert running == {"turn_count": 4, "is_ended": False}


@pytest.mark.asyncio
@respx.mock
async def test_outcome_text_is_sent_and_capped_to_what_core_api_accepts() -> None:
    settings = get_settings()
    playthrough_id = uuid4()
    url = f"{settings.core_api_url}/internal/v1/playthroughs/{playthrough_id}/outcome-text"
    route = respx.patch(url).respond(status_code=200)

    await sync_outcome_text(playthrough_id, "x" * (OUTCOME_TEXT_MAX_CHARS + 50))

    sent = json.loads(route.calls.last.request.content)
    assert sent == {"ended_outcome_text": "x" * OUTCOME_TEXT_MAX_CHARS}


@pytest.mark.asyncio
@respx.mock
async def test_a_failed_outcome_text_hand_off_never_raises() -> None:
    settings = get_settings()
    playthrough_id = uuid4()
    url = f"{settings.core_api_url}/internal/v1/playthroughs/{playthrough_id}/outcome-text"
    respx.patch(url).mock(side_effect=httpx.ConnectError("down"))

    await sync_outcome_text(playthrough_id, "A quiet ending.")

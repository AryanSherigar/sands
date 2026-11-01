"""Unit tests for context_retrieval.py, with the memory client mocked."""

import json
import uuid

import pytest
import structlog
from app.exceptions.memory_exceptions import CODE_NOT_REGISTERED, MemoryRetrieveError
from app.integrations import memory_client
from app.models.memory import (
    REASON_MEMORY_DISABLED,
    REASON_RETRIEVAL_FAILED,
    RetrieveRequest,
    RetrieveResponse,
    Watermarks,
)
from app.models.turn import LoadedState, RecentTurn, TurnRequest
from app.services import memory_relay_service
from app.turn.steps import context_retrieval


def _turn_request() -> TurnRequest:
    return TurnRequest(
        playthrough_id=uuid.uuid4(),
        participant_id=uuid.uuid4(),
        client_action_id=uuid.uuid4(),
        action_text="CANARY-ACTION-TEXT",
        action_mode="say",
        turn_count=3,
    )


def _loaded_state(revision: int | None = 1) -> LoadedState:
    return LoadedState(
        scenario_id=uuid.uuid4(),
        scenario_snapshot={"mode": "newbie"},
        state={},
        turn_count=3,
        checkpoint=None,
        memory_publish_revision=revision,
    )


def _response(reasons: list[str] | None = None) -> RetrieveResponse:
    return RetrieveResponse(
        items=[],
        active_entities=[],
        scene=None,
        watermarks=Watermarks(
            ingested_seq=3, indexed_seq=3, extracted_seq=0, latest_seq_seen=3
        ),
        degraded_reasons=reasons or [],
        embedding_model="test",
    )


async def test_success_returns_the_response_and_its_degraded_reasons(
    monkeypatch,
) -> None:
    seen: list[RetrieveRequest] = []

    async def fake_retrieve(request):
        seen.append(request)
        return _response(["template_missing"])

    monkeypatch.setattr(memory_client, "retrieve", fake_retrieve)
    turn_request = _turn_request()

    context = await context_retrieval.retrieve_context(
        turn_request, _loaded_state(), [], {}
    )

    assert context.response is not None
    assert context.reasons == ["template_missing"]
    assert context.should_inline_lore_fallback
    assert seen[0].playthrough_id == turn_request.playthrough_id
    assert seen[0].sequence == 3


@pytest.mark.parametrize(
    "error",
    [
        MemoryRetrieveError("unavailable"),
        MemoryRetrieveError("server_error", 500),
        RuntimeError("unexpected"),
    ],
)
async def test_any_failure_yields_an_empty_context_with_retrieval_failed(
    monkeypatch, error: Exception
) -> None:
    async def failing_retrieve(request):
        raise error

    monkeypatch.setattr(memory_client, "retrieve", failing_retrieve)

    context = await context_retrieval.retrieve_context(
        _turn_request(), _loaded_state(), [], {}
    )

    assert context.response is None
    assert context.items == []
    assert context.reasons == [REASON_RETRIEVAL_FAILED]
    assert context.should_inline_lore_fallback


async def test_not_registered_delivers_once_then_retries_once(monkeypatch) -> None:
    calls: list[str] = []

    async def fake_retrieve(request):
        calls.append("retrieve")
        if calls.count("retrieve") == 1:
            raise MemoryRetrieveError(CODE_NOT_REGISTERED, 409)
        return _response()

    async def fake_deliver(playthrough_id):
        calls.append("deliver")

    monkeypatch.setattr(memory_client, "retrieve", fake_retrieve)
    monkeypatch.setattr(memory_relay_service, "deliver_best_effort", fake_deliver)
    monkeypatch.setattr(
        context_retrieval.settings, "memory_registration_retry_delay_seconds", 0
    )

    context = await context_retrieval.retrieve_context(
        _turn_request(), _loaded_state(), [], {}
    )

    assert calls == ["retrieve", "deliver", "retrieve"]
    assert context.response is not None
    assert context.reasons == []


async def test_not_registered_retry_waits_for_the_configured_delay(
    monkeypatch,
) -> None:
    sleeps: list[float] = []

    async def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    async def fake_retrieve(request):
        if not sleeps:
            raise MemoryRetrieveError(CODE_NOT_REGISTERED, 409)
        return _response()

    async def fake_deliver(playthrough_id):
        return None

    monkeypatch.setattr(context_retrieval.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(
        context_retrieval.settings, "memory_registration_retry_delay_seconds", 0.25
    )
    monkeypatch.setattr(memory_client, "retrieve", fake_retrieve)
    monkeypatch.setattr(memory_relay_service, "deliver_best_effort", fake_deliver)

    context = await context_retrieval.retrieve_context(
        _turn_request(), _loaded_state(), [], {}
    )

    assert sleeps == [0.25]
    assert context.response is not None


async def test_not_registered_twice_gives_up_after_one_retry(monkeypatch) -> None:
    calls: list[str] = []

    async def always_unregistered(request):
        calls.append("retrieve")
        raise MemoryRetrieveError(CODE_NOT_REGISTERED, 409)

    async def fake_deliver(playthrough_id):
        calls.append("deliver")

    monkeypatch.setattr(memory_client, "retrieve", always_unregistered)
    monkeypatch.setattr(memory_relay_service, "deliver_best_effort", fake_deliver)
    monkeypatch.setattr(
        context_retrieval.settings, "memory_registration_retry_delay_seconds", 0
    )

    context = await context_retrieval.retrieve_context(
        _turn_request(), _loaded_state(), [], {}
    )

    assert calls == ["retrieve", "deliver", "retrieve"]
    assert context.reasons == [REASON_RETRIEVAL_FAILED]


async def test_other_errors_do_not_trigger_a_delivery(monkeypatch) -> None:
    delivered: list[uuid.UUID] = []

    async def failing_retrieve(request):
        raise MemoryRetrieveError("unavailable")

    async def fake_deliver(playthrough_id):
        delivered.append(playthrough_id)

    monkeypatch.setattr(memory_client, "retrieve", failing_retrieve)
    monkeypatch.setattr(memory_relay_service, "deliver_best_effort", fake_deliver)

    await context_retrieval.retrieve_context(_turn_request(), _loaded_state(), [], {})

    assert delivered == []


async def test_playthrough_without_a_pinned_revision_never_calls_memory(
    monkeypatch,
) -> None:
    calls: list[RetrieveRequest] = []

    async def recording_retrieve(request):
        calls.append(request)
        return _response()

    monkeypatch.setattr(memory_client, "retrieve", recording_retrieve)

    context = await context_retrieval.retrieve_context(
        _turn_request(), _loaded_state(revision=None), [], {}
    )

    assert calls == []
    assert context.reasons == [REASON_RETRIEVAL_FAILED]
    assert context.response is None


async def test_recent_turns_reach_the_request_query_text(monkeypatch) -> None:
    seen: list[RetrieveRequest] = []

    async def fake_retrieve(request):
        seen.append(request)
        return _response()

    monkeypatch.setattr(memory_client, "retrieve", fake_retrieve)
    recent = [
        RecentTurn(
            turn_number=3,
            participant_id=None,
            action_mode="say",
            action_text="Bring the key",
            narration_text="She nods.",
        )
    ]

    await context_retrieval.retrieve_context(
        _turn_request(), _loaded_state(), recent, {}
    )

    assert seen[0].last_actor_utterance == "Bring the key"
    assert "She nods." in seen[0].recent_text


async def test_player_text_is_never_logged(monkeypatch) -> None:
    async def failing_retrieve(request):
        raise MemoryRetrieveError("unavailable")

    monkeypatch.setattr(memory_client, "retrieve", failing_retrieve)

    with structlog.testing.capture_logs() as captured:
        await context_retrieval.retrieve_context(
            _turn_request(), _loaded_state(), [], {}
        )

    assert captured
    assert "CANARY-ACTION-TEXT" not in json.dumps(captured, default=str)


async def test_disabled_memory_skips_the_call_and_asks_for_the_lore_fallback(
    monkeypatch,
) -> None:
    async def _must_not_be_called(request: RetrieveRequest) -> RetrieveResponse:
        raise AssertionError("memory must not be called when retrieval is disabled")

    monkeypatch.setattr(memory_client, "retrieve", _must_not_be_called)
    monkeypatch.setattr(context_retrieval.settings, "memory_retrieval_enabled", False)

    context = await context_retrieval.retrieve_context(
        _turn_request(), _loaded_state(), [], {}
    )

    assert context.response is None
    assert context.reasons == [REASON_MEMORY_DISABLED]
    assert context.should_inline_lore_fallback is True

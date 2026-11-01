"""Unit tests for the real memory_client.py, with HTTP mocked via respx."""

import json
from uuid import uuid4

import httpx
import pytest
import respx
import structlog
from app.config import settings
from app.exceptions.memory_exceptions import MemoryIngestError, MemoryRetrieveError
from app.integrations import memory_client
from app.models.memory import RetrieveRequest
from app.models.memory_ingest import FlushItem, IngestRequest


@pytest.fixture(autouse=True)
def _reset_client_singleton(monkeypatch):
    """Ensure each test builds a fresh client against the current settings."""
    monkeypatch.setattr(memory_client, "_client", None)
    yield
    monkeypatch.setattr(memory_client, "_client", None)


def _flush_request() -> IngestRequest:
    return IngestRequest(playthrough_id=uuid4(), items=[FlushItem(sequence=3)])


def _ingest_ok(request: IngestRequest) -> dict:
    return {
        "playthrough_id": str(request.playthrough_id),
        "ingested_seq": 3,
        "latest_seq_seen": 3,
        "items": [{"item_kind": "flush", "sequence": 3, "outcome": "applied"}],
    }


@pytest.mark.asyncio
async def test_ingest_items_posts_to_memory_with_service_name_header() -> None:
    request = _flush_request()
    with respx.mock(base_url=settings.memory_url) as router:
        route = router.post("/v1/ingest/items").mock(
            return_value=httpx.Response(200, json=_ingest_ok(request))
        )
        response = await memory_client.ingest_items(request)

    assert response.ingested_seq == 3
    assert json.loads(route.calls[0].request.content) == {
        "delivery_id": None,
        "playthrough_id": str(request.playthrough_id),
        "items": [{"item_kind": "flush", "sequence": 3}],
    }
    assert route.calls[0].request.headers["x-dev-service-name"] == (
        settings.memory_service_name
    )


@pytest.mark.asyncio
async def test_ingest_items_forwards_delivery_id() -> None:
    delivery_id = uuid4()
    request = _flush_request().model_copy(update={"delivery_id": delivery_id})
    with respx.mock(base_url=settings.memory_url) as router:
        route = router.post("/v1/ingest/items").mock(
            return_value=httpx.Response(200, json=_ingest_ok(request))
        )
        await memory_client.ingest_items(request)

    assert json.loads(route.calls[0].request.content)["delivery_id"] == str(delivery_id)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "code", "status"),
    [
        (
            httpx.Response(409, json={"detail": "x", "code": "not_registered"}),
            "not_registered",
            409,
        ),
        (
            httpx.Response(422, json={"detail": "x", "code": "batch_too_large"}),
            "batch_too_large",
            422,
        ),
        (httpx.Response(502, text="<html>gateway</html>"), "unknown", 502),
        (httpx.Response(500, json=["not", "a", "dict"]), "unknown", 500),
        (httpx.Response(200, json={"unexpected": 1}), "invalid_response", 200),
    ],
)
async def test_ingest_items_maps_failures_to_typed_errors(
    response: httpx.Response, code: str, status: int
) -> None:
    with respx.mock(base_url=settings.memory_url) as router:
        router.post("/v1/ingest/items").mock(return_value=response)
        with pytest.raises(MemoryIngestError) as error:
            await memory_client.ingest_items(_flush_request())

    assert (error.value.code, error.value.upstream_status) == (code, status)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")]
)
async def test_ingest_items_maps_transport_failures_to_unavailable(
    failure: Exception,
) -> None:
    with respx.mock(base_url=settings.memory_url) as router:
        router.post("/v1/ingest/items").mock(side_effect=failure)
        with pytest.raises(MemoryIngestError) as error:
            await memory_client.ingest_items(_flush_request())

    assert (error.value.code, error.value.upstream_status) == ("unavailable", None)


@pytest.mark.asyncio
async def test_ingest_items_never_logs_response_text() -> None:
    canary = "CANARY-UPSTREAM-TEXT"
    with (
        structlog.testing.capture_logs() as captured,
        respx.mock(base_url=settings.memory_url) as router,
    ):
        router.post("/v1/ingest/items").mock(
            return_value=httpx.Response(500, text=canary)
        )
        with pytest.raises(MemoryIngestError):
            await memory_client.ingest_items(_flush_request())

    assert captured
    assert canary not in json.dumps(captured, default=str)


def _retrieve_request() -> RetrieveRequest:
    return RetrieveRequest(
        playthrough_id=uuid4(),
        sequence=7,
        action_text="I return to Mara",
        action_mode="say",
        actor_participant_id=uuid4(),
        recent_text="Player: hello\nNarrator: hi",
        recent_window_turns=6,
    )


def _retrieve_ok() -> dict:
    return {
        "items": [
            {
                "kind": "fact",
                "item_id": str(uuid4()),
                "source_kind": "fact",
                "authority": "authored",
                "assertion": "occurred",
                "sequence": 0,
                "speaker": None,
                "text": "Mara owns the forge",
                "entity_ids": [],
                "branches": ["exact"],
            }
        ],
        "active_entities": [],
        "scene": None,
        "watermarks": {
            "ingested_seq": 7,
            "indexed_seq": 7,
            "extracted_seq": 0,
            "latest_seq_seen": 7,
        },
        "degraded_reasons": ["template_missing"],
        "embedding_model": "text-embedding-005",
        "skipped_branches": ["vector"],
    }


@pytest.mark.asyncio
async def test_retrieve_posts_request_with_service_name_header_and_parses() -> None:
    request = _retrieve_request()
    with respx.mock(base_url=settings.memory_url) as router:
        route = router.post("/v1/retrieve").mock(
            return_value=httpx.Response(200, json=_retrieve_ok())
        )
        response = await memory_client.retrieve(request)

    sent = route.calls[0].request
    body = json.loads(sent.content)
    assert body["playthrough_id"] == str(request.playthrough_id)
    assert body["sequence"] == 7
    assert body["recent_window_turns"] == 6
    assert sent.headers["x-dev-service-name"] == settings.memory_service_name
    assert response.items[0].text == "Mara owns the forge"
    assert response.degraded_reasons == ["template_missing"]
    assert response.skipped_branches == ["vector"]


@pytest.mark.asyncio
async def test_retrieve_uses_the_configured_timeout(monkeypatch) -> None:
    monkeypatch.setattr(settings, "memory_retrieve_timeout_seconds", 0.25)
    with respx.mock(base_url=settings.memory_url) as router:
        route = router.post("/v1/retrieve").mock(
            return_value=httpx.Response(200, json=_retrieve_ok())
        )
        await memory_client.retrieve(_retrieve_request())

    assert route.calls[0].request.extensions["timeout"]["read"] == 0.25


@pytest.mark.asyncio
async def test_retrieve_not_registered_is_a_typed_error() -> None:
    with respx.mock(base_url=settings.memory_url) as router:
        router.post("/v1/retrieve").mock(
            return_value=httpx.Response(
                409, json={"detail": "x", "code": "not_registered"}
            )
        )
        with pytest.raises(MemoryRetrieveError) as error:
            await memory_client.retrieve(_retrieve_request())

    assert error.value.is_not_registered
    assert error.value.upstream_status == 409


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("response", "code", "status"),
    [
        (
            httpx.Response(422, json={"code": "request_too_large"}),
            "request_too_large",
            422,
        ),
        (httpx.Response(502, text="<html>gateway</html>"), "unknown", 502),
        (httpx.Response(200, json={"unexpected": 1}), "invalid_response", 200),
    ],
)
async def test_retrieve_maps_failures_to_typed_errors(
    response: httpx.Response, code: str, status: int
) -> None:
    with respx.mock(base_url=settings.memory_url) as router:
        router.post("/v1/retrieve").mock(return_value=response)
        with pytest.raises(MemoryRetrieveError) as error:
            await memory_client.retrieve(_retrieve_request())

    assert (error.value.code, error.value.upstream_status) == (code, status)
    assert not error.value.is_not_registered


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "failure", [httpx.ConnectError("refused"), httpx.ReadTimeout("slow")]
)
async def test_retrieve_maps_transport_failures_to_unavailable(
    failure: Exception,
) -> None:
    with respx.mock(base_url=settings.memory_url) as router:
        router.post("/v1/retrieve").mock(side_effect=failure)
        with pytest.raises(MemoryRetrieveError) as error:
            await memory_client.retrieve(_retrieve_request())

    assert (error.value.code, error.value.upstream_status) == ("unavailable", None)


@pytest.mark.asyncio
async def test_retrieve_never_logs_player_or_response_text() -> None:
    canary = "CANARY-UPSTREAM-TEXT"
    request = _retrieve_request().model_copy(
        update={"action_text": "CANARY-PLAYER-ACTION"}
    )
    with (
        structlog.testing.capture_logs() as captured,
        respx.mock(base_url=settings.memory_url) as router,
    ):
        router.post("/v1/retrieve").mock(return_value=httpx.Response(500, text=canary))
        with pytest.raises(MemoryRetrieveError):
            await memory_client.retrieve(request)

    logged = json.dumps(captured, default=str)
    assert captured
    assert canary not in logged
    assert "CANARY-PLAYER-ACTION" not in logged


@pytest.mark.asyncio
async def test_retry_memory_posts_to_the_playthrough_retry_path() -> None:
    playthrough_id = uuid4()
    body = {
        "batches_reset": 1,
        "failures_reset": 0,
        "process_pending": {"embedding_step": "idle"},
        "degraded_reasons": ["indexing_lag"],
    }
    with respx.mock(base_url=settings.memory_url) as router:
        route = router.post(f"/v1/playthroughs/{playthrough_id}/memory/retry").mock(
            return_value=httpx.Response(200, json=body)
        )
        result = await memory_client.retry_memory(playthrough_id)

    assert route.call_count == 1
    assert (result.batches_reset, result.degraded_reasons) == (1, ["indexing_lag"])


@pytest.mark.asyncio
async def test_retry_memory_raises_with_memorys_error_code() -> None:
    from app.exceptions.memory_exceptions import MemoryRetryError

    playthrough_id = uuid4()
    with respx.mock(base_url=settings.memory_url) as router:
        router.post(f"/v1/playthroughs/{playthrough_id}/memory/retry").mock(
            return_value=httpx.Response(
                409, json={"detail": "x", "code": "not_registered"}
            )
        )
        with pytest.raises(MemoryRetryError) as raised:
            await memory_client.retry_memory(playthrough_id)

    assert (raised.value.code, raised.value.upstream_status) == ("not_registered", 409)


@pytest.mark.asyncio
async def test_retry_memory_maps_transport_errors_to_unavailable() -> None:
    from app.exceptions.memory_exceptions import MemoryRetryError

    playthrough_id = uuid4()
    with respx.mock(base_url=settings.memory_url) as router:
        router.post(f"/v1/playthroughs/{playthrough_id}/memory/retry").mock(
            side_effect=httpx.ConnectError("refused")
        )
        with pytest.raises(MemoryRetryError) as raised:
            await memory_client.retry_memory(playthrough_id)

    assert raised.value.code == "unavailable"

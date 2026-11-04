"""Unit tests for the real memory_client.py, with the memory services' HTTP surfaces mocked via respx."""

import json
from uuid import UUID, uuid4

import httpx
import pytest
import respx
from app.config import settings
from app.exceptions.memory_exceptions import (
    MemoryPurgeError,
    MemoryTemplateBuildError,
)
from app.integrations import memory_client
from app.models.memory_template import NewbieTemplateContent, TemplateBuildRequest


@pytest.fixture(autouse=True)
def _reset_client_singleton():
    memory_client._client = None
    yield
    memory_client._client = None


TEMPLATE_URL = settings.memory_url


def _build_request(publish_revision: int = 1) -> TemplateBuildRequest:
    return TemplateBuildRequest(
        scenario_id=uuid4(),
        publish_revision=publish_revision,
        mode="newbie",
        content_hash="abc123",
        newbie=NewbieTemplateContent(world_lore="Once upon a time."),
    )


def _build_response_body(direct_status: str = "ready") -> dict[str, str]:
    return {
        "template_id": str(uuid4()),
        "direct_status": direct_status,
        "enrichment_status": "pending",
    }


@pytest.mark.asyncio
@respx.mock
async def test_build_template_posts_to_templates_with_service_identity_header() -> None:
    route = respx.post(f"{TEMPLATE_URL}/v1/templates").mock(
        return_value=httpx.Response(201, json=_build_response_body())
    )
    request = _build_request()

    outcome = await memory_client.build_template(request)

    assert outcome.was_created is True
    assert outcome.response.direct_status == "ready"
    sent = route.calls[0].request
    assert sent.headers["x-dev-service-name"] == settings.memory_service_name
    body = json.loads(sent.content)
    assert body["publish_revision"] == 1
    assert body["content_hash"] == "abc123"
    assert body["newbie"]["world_lore"] == "Once upon a time."


@pytest.mark.asyncio
@respx.mock
async def test_build_template_idempotent_replay_is_not_reported_as_created() -> None:
    respx.post(f"{TEMPLATE_URL}/v1/templates").mock(
        return_value=httpx.Response(200, json=_build_response_body())
    )

    outcome = await memory_client.build_template(_build_request())

    assert outcome.was_created is False


@pytest.mark.asyncio
@respx.mock
async def test_build_template_error_carries_only_code_and_status() -> None:
    respx.post(f"{TEMPLATE_URL}/v1/templates").mock(
        return_value=httpx.Response(
            409,
            json={"code": "template_content_conflict", "message": "secret lore text"},
        )
    )

    with pytest.raises(MemoryTemplateBuildError) as excinfo:
        await memory_client.build_template(_build_request())

    assert excinfo.value.code == "template_content_conflict"
    assert excinfo.value.upstream_status == 409
    assert "secret lore text" not in excinfo.value.message


@pytest.mark.asyncio
@respx.mock
async def test_build_template_transport_failure_maps_to_unavailable() -> None:
    respx.post(f"{TEMPLATE_URL}/v1/templates").mock(
        side_effect=httpx.ConnectError("refused")
    )

    with pytest.raises(MemoryTemplateBuildError) as excinfo:
        await memory_client.build_template(_build_request())

    assert excinfo.value.code == "unavailable"


@pytest.mark.asyncio
@respx.mock
async def test_build_template_non_json_error_body_maps_to_unknown_code() -> None:
    respx.post(f"{TEMPLATE_URL}/v1/templates").mock(
        return_value=httpx.Response(502, text="<html>bad gateway</html>")
    )

    with pytest.raises(MemoryTemplateBuildError) as excinfo:
        await memory_client.build_template(_build_request())

    assert excinfo.value.code == "unknown"
    assert excinfo.value.upstream_status == 502


@pytest.mark.asyncio
@respx.mock
async def test_build_template_invalid_success_body_is_an_error() -> None:
    respx.post(f"{TEMPLATE_URL}/v1/templates").mock(
        return_value=httpx.Response(200, json={"unexpected": True})
    )

    with pytest.raises(MemoryTemplateBuildError) as excinfo:
        await memory_client.build_template(_build_request())

    assert excinfo.value.code == "invalid_response"


@pytest.mark.asyncio
async def test_close_memory_client_resets_singleton() -> None:
    memory_client._get_client()
    assert memory_client._client is not None

    await memory_client.close_memory_client()

    assert memory_client._client is None


@pytest.mark.asyncio
async def test_close_memory_client_is_a_no_op_when_already_closed() -> None:
    assert memory_client._client is None

    await memory_client.close_memory_client()

    assert memory_client._client is None


PURGE_URL = f"{TEMPLATE_URL}/v1/purge"
SCOPES_URL = f"{TEMPLATE_URL}/v1/scopes"


def _purge_response(
    playthroughs: int = 0, purged: int = 0, retained: int = 0
) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "playthroughs_purged": playthroughs,
            "templates_purged": purged,
            "templates_retained_in_use": retained,
        },
    )


def _sent_body(call: respx.models.Call) -> dict[str, list[str]]:
    return json.loads(call.request.content)


@pytest.mark.asyncio
@respx.mock
async def test_purge_posts_ids_with_service_identity_header() -> None:
    playthrough_id, scenario_id = uuid4(), uuid4()
    route = respx.post(PURGE_URL).mock(return_value=_purge_response(1, 2, 3))

    result = await memory_client.purge([playthrough_id], [scenario_id])

    assert (result.playthroughs_purged, result.templates_purged) == (1, 2)
    assert result.templates_retained_in_use == 3
    sent = route.calls[0].request
    assert sent.headers["x-dev-service-name"] == settings.memory_service_name
    assert _sent_body(route.calls[0]) == {
        "playthrough_ids": [str(playthrough_id)],
        "scenario_ids": [str(scenario_id)],
    }


@pytest.mark.asyncio
@respx.mock
async def test_purge_uses_the_purge_timeout() -> None:
    route = respx.post(PURGE_URL).mock(return_value=_purge_response())

    await memory_client.purge(scenario_ids=[uuid4()])

    timeout = route.calls[0].request.extensions["timeout"]
    assert timeout["read"] == settings.memory_purge_timeout_seconds


@pytest.mark.asyncio
@respx.mock
async def test_purge_without_ids_makes_no_call() -> None:
    route = respx.post(PURGE_URL).mock(return_value=_purge_response(9, 9, 9))

    result = await memory_client.purge([], [])

    assert not route.called
    assert result.model_dump() == {
        "playthroughs_purged": 0,
        "templates_purged": 0,
        "templates_retained_in_use": 0,
    }


@pytest.mark.asyncio
@respx.mock
async def test_purge_chunks_to_one_hundred_ids_playthroughs_first_and_sums() -> None:
    playthrough_ids = [uuid4() for _ in range(150)]
    scenario_ids = [uuid4() for _ in range(30)]
    route = respx.post(PURGE_URL).mock(return_value=_purge_response(10, 1, 2))

    result = await memory_client.purge(playthrough_ids, scenario_ids)

    bodies = [_sent_body(call) for call in route.calls]
    assert len(bodies) == 3
    assert all(
        len(body["playthrough_ids"]) + len(body["scenario_ids"]) <= 100
        for body in bodies
    )
    assert [len(body["playthrough_ids"]) for body in bodies] == [100, 50, 0]
    assert [len(body["scenario_ids"]) for body in bodies] == [0, 0, 30]
    sent_playthroughs = [i for body in bodies for i in body["playthrough_ids"]]
    assert sent_playthroughs == [str(i) for i in playthrough_ids]
    assert (result.playthroughs_purged, result.templates_purged) == (30, 3)
    assert result.templates_retained_in_use == 6


@pytest.mark.asyncio
@respx.mock
async def test_purge_stops_at_first_failing_chunk() -> None:
    route = respx.post(PURGE_URL).mock(
        side_effect=[
            _purge_response(),
            httpx.Response(503, json={"code": "db_down"}),
            _purge_response(),
        ]
    )

    with pytest.raises(MemoryPurgeError) as excinfo:
        await memory_client.purge([uuid4() for _ in range(250)])

    assert excinfo.value.code == "db_down"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_purge_error_carries_only_code_and_status() -> None:
    respx.post(PURGE_URL).mock(
        return_value=httpx.Response(
            422, json={"code": "too_many_ids", "message": "secret lore text"}
        )
    )

    with pytest.raises(MemoryPurgeError) as excinfo:
        await memory_client.purge([uuid4()])

    assert excinfo.value.code == "too_many_ids"
    assert excinfo.value.upstream_status == 422
    assert "secret lore text" not in excinfo.value.message


@pytest.mark.asyncio
@respx.mock
async def test_purge_transport_failure_maps_to_unavailable() -> None:
    respx.post(PURGE_URL).mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(MemoryPurgeError) as excinfo:
        await memory_client.purge([uuid4()])

    assert excinfo.value.code == "unavailable"
    assert excinfo.value.upstream_status is None


@pytest.mark.asyncio
@respx.mock
async def test_purge_timeout_maps_to_unavailable() -> None:
    respx.post(PURGE_URL).mock(side_effect=httpx.ReadTimeout("slow"))

    with pytest.raises(MemoryPurgeError) as excinfo:
        await memory_client.purge(scenario_ids=[uuid4()])

    assert excinfo.value.code == "unavailable"


@pytest.mark.asyncio
@respx.mock
async def test_purge_non_json_error_body_maps_to_unknown_code() -> None:
    respx.post(PURGE_URL).mock(
        return_value=httpx.Response(502, text="<html>bad gateway</html>")
    )

    with pytest.raises(MemoryPurgeError) as excinfo:
        await memory_client.purge([uuid4()])

    assert excinfo.value.code == "unknown"
    assert excinfo.value.upstream_status == 502


@pytest.mark.asyncio
@respx.mock
async def test_purge_error_body_without_code_maps_to_unknown_code() -> None:
    respx.post(PURGE_URL).mock(
        return_value=httpx.Response(500, json={"detail": "boom"})
    )

    with pytest.raises(MemoryPurgeError) as excinfo:
        await memory_client.purge([uuid4()])

    assert excinfo.value.code == "unknown"


@pytest.mark.asyncio
@respx.mock
async def test_purge_non_json_success_body_is_invalid_response() -> None:
    respx.post(PURGE_URL).mock(return_value=httpx.Response(200, text="ok"))

    with pytest.raises(MemoryPurgeError) as excinfo:
        await memory_client.purge([uuid4()])

    assert excinfo.value.code == "invalid_response"
    assert excinfo.value.upstream_status == 200


@pytest.mark.asyncio
@respx.mock
async def test_purge_invalid_success_body_is_invalid_response() -> None:
    respx.post(PURGE_URL).mock(
        return_value=httpx.Response(200, json={"playthroughs_purged": "many"})
    )

    with pytest.raises(MemoryPurgeError) as excinfo:
        await memory_client.purge([uuid4()])

    assert excinfo.value.code == "invalid_response"


def _scopes_body(playthrough_id: UUID, scenario_id: UUID) -> dict[str, object]:
    return {
        "playthroughs": [
            {
                "playthrough_id": str(playthrough_id),
                "created_at": "2026-10-27T10:00:00Z",
            }
        ],
        "templates": [
            {
                "template_id": str(uuid4()),
                "scenario_id": str(scenario_id),
                "publish_revision": 2,
                "created_at": "2026-10-27T10:00:00+00:00",
            }
        ],
    }


@pytest.mark.asyncio
@respx.mock
async def test_list_scopes_returns_typed_scopes_with_service_identity_header() -> None:
    playthrough_id, scenario_id = uuid4(), uuid4()
    route = respx.get(SCOPES_URL).mock(
        return_value=httpx.Response(200, json=_scopes_body(playthrough_id, scenario_id))
    )

    scopes = await memory_client.list_scopes()

    assert route.calls[0].request.headers["x-dev-service-name"] == (
        settings.memory_service_name
    )
    assert scopes.playthroughs[0].playthrough_id == playthrough_id
    assert scopes.playthroughs[0].created_at.utcoffset() is not None
    assert scopes.templates[0].scenario_id == scenario_id
    assert scopes.templates[0].publish_revision == 2


@pytest.mark.asyncio
@respx.mock
async def test_list_scopes_treats_naive_timestamps_as_utc() -> None:
    body = _scopes_body(uuid4(), uuid4())
    body["playthroughs"][0]["created_at"] = "2026-10-27T10:00:00"  # type: ignore[index]
    respx.get(SCOPES_URL).mock(return_value=httpx.Response(200, json=body))

    scopes = await memory_client.list_scopes()

    assert scopes.playthroughs[0].created_at.tzinfo is not None


@pytest.mark.asyncio
@respx.mock
async def test_list_scopes_transport_failure_maps_to_unavailable() -> None:
    respx.get(SCOPES_URL).mock(side_effect=httpx.ConnectError("refused"))

    with pytest.raises(MemoryPurgeError) as excinfo:
        await memory_client.list_scopes()

    assert excinfo.value.code == "unavailable"


@pytest.mark.asyncio
@respx.mock
async def test_list_scopes_non_2xx_and_invalid_body_raise_purge_errors() -> None:
    respx.get(SCOPES_URL).mock(
        side_effect=[
            httpx.Response(500, json={"code": "scan_failed"}),
            httpx.Response(200, json={"playthroughs": "nope"}),
            httpx.Response(200, text="not json"),
        ]
    )

    codes = []
    for _ in range(3):
        with pytest.raises(MemoryPurgeError) as excinfo:
            await memory_client.list_scopes()
        codes.append((excinfo.value.code, excinfo.value.upstream_status))

    assert codes == [
        ("scan_failed", 500),
        ("invalid_response", 200),
        ("invalid_response", 200),
    ]

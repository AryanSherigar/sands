"""Integration tests for POST /v1/scenes/{scene_id}/messages."""

import uuid

import pytest
from app.config import settings
from app.exceptions.scene_exceptions import SceneNotFoundError
from app.integrations import openai_compatible_client, simulation_client
from app.services.rate_limit.policies import match_burst_policy
from httpx import AsyncClient
from strategy_contracts.scene import SceneStatus, SubmissionStatus
from strategy_contracts.scene_exchange import SceneExchangeResult
from tests.services.test_scene_service import _fetched

SCENE_ID = uuid.uuid4()
PATH = f"/v1/scenes/{SCENE_ID}/messages"


def _headers() -> dict[str, str]:
    return {"X-Dev-User-Id": str(uuid.uuid4())}


@pytest.fixture
def narrator(monkeypatch):
    async def fake_stream_chat(system_instruction, contents, **_):
        is_decision = "Answer with only a JSON" in contents[-1].parts[0].text
        yield '{"action": "continue_talk"}' if is_decision else "Speak plainly."

    async def fake_submit(scene_id, user_id, submission):
        return SceneExchangeResult(
            status=SubmissionStatus.ACCEPTED,
            scene_status=SceneStatus.OPENED,
            exchanges_remaining=5,
        )

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)
    monkeypatch.setattr(simulation_client, "submit_exchange", fake_submit)


def _serve(monkeypatch, fetched=None, error=None):
    async def fake_fetch(scene_id, user_id):
        if error is not None:
            raise error
        return fetched or _fetched()

    monkeypatch.setattr(simulation_client, "fetch_scene_package", fake_fetch)


async def test_requires_auth(async_client: AsyncClient) -> None:
    response = await async_client.post(PATH, json={"text": "hello"})
    assert response.status_code == 401


@pytest.mark.parametrize("text", ["", "x" * 10_000])
async def test_rejects_empty_and_oversized_messages(
    async_client: AsyncClient, monkeypatch, text
) -> None:
    _serve(monkeypatch)
    response = await async_client.post(PATH, json={"text": text}, headers=_headers())
    assert response.status_code == 422


async def test_streams_narration_then_done(
    async_client: AsyncClient, monkeypatch, narrator
) -> None:
    _serve(monkeypatch)
    response = await async_client.post(
        PATH, json={"text": "Will you sign?"}, headers=_headers()
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: narration" in response.text
    assert "Speak plainly." in response.text
    assert "event: done" in response.text
    assert "agree outright" not in response.text


async def test_a_finished_scene_is_a_conflict_before_streaming(
    async_client: AsyncClient, monkeypatch, narrator
) -> None:
    _serve(monkeypatch, _fetched(SceneStatus.RESOLVED))
    response = await async_client.post(PATH, json={"text": "hi"}, headers=_headers())
    assert response.status_code == 409
    assert response.json()["code"] == "scene_not_open"


async def test_an_unknown_scene_is_not_found(
    async_client: AsyncClient, monkeypatch, narrator
) -> None:
    _serve(monkeypatch, error=SceneNotFoundError())
    response = await async_client.post(PATH, json={"text": "hi"}, headers=_headers())
    assert response.status_code == 404
    assert response.json()["code"] == "scene_not_found"


def test_scene_messages_have_their_own_burst_policy() -> None:
    policy = match_burst_policy("POST", PATH, is_authenticated=True)
    assert policy.group == "scene"
    assert policy.limit == settings.rate_limit_scene_per_window


async def test_a_letter_open_streams_the_letter_and_stores_it(
    async_client: AsyncClient, monkeypatch
) -> None:
    from tests.services import letter_fixtures

    stored: list[str] = []

    async def fake_stream_chat(system_instruction, contents, **_):
        yield "Valdren, the fords are watched."

    async def fake_store(scene_id, user_id, text):
        stored.append(text)
        return SceneExchangeResult(
            status=SubmissionStatus.ACCEPTED,
            scene_status=SceneStatus.OPENED,
            exchanges_remaining=1,
        )

    monkeypatch.setattr(openai_compatible_client, "stream_chat", fake_stream_chat)
    monkeypatch.setattr(simulation_client, "store_letter_body", fake_store)
    _serve(monkeypatch, letter_fixtures.fetched())

    response = await async_client.post(PATH, json={"kind": "open"}, headers=_headers())

    assert response.status_code == 200
    assert "Valdren, the fords are watched." in response.text
    assert "event: done" in response.text
    assert stored == ["Valdren, the fords are watched."]


@pytest.mark.parametrize(
    "body",
    [
        {"kind": "seal", "text": ""},
        {"kind": "seal", "text": "x" * 1_201},
        {"kind": "scribe", "text": "x" * 301},
        {"kind": "unknown", "text": "hello"},
    ],
)
async def test_invalid_letter_messages_are_rejected_before_any_lookup(
    async_client: AsyncClient, monkeypatch, body
) -> None:
    _serve(monkeypatch)
    response = await async_client.post(PATH, json=body, headers=_headers())
    assert response.status_code == 422


async def test_a_letter_kind_on_a_negotiation_is_a_422_kind_mismatch(
    async_client: AsyncClient, monkeypatch, narrator
) -> None:
    _serve(monkeypatch)
    response = await async_client.post(PATH, json={"kind": "open"}, headers=_headers())
    assert response.status_code == 422
    assert response.json()["code"] == "scene_kind_mismatch"

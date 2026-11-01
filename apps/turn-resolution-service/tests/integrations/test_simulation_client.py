import json
import uuid

import httpx
import pytest
import respx
from app.config import settings
from app.exceptions.scene_exceptions import (
    SceneNotFoundError,
    SceneNotOpenError,
    SimulationUnavailableError,
)
from app.integrations import simulation_client
from strategy_contracts.scene_exchange import SceneExchangeSubmission

SCENE_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
USER_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
PACKAGE_URL = f"/internal/v1/scenes/{SCENE_ID}/package"
EXCHANGE_URL = f"/internal/v1/scenes/{SCENE_ID}/exchanges"
TOKEN = "service-token"


@pytest.fixture(autouse=True)
def _configured(monkeypatch):
    monkeypatch.setattr(settings, "simulation_url", "http://simulation.test")
    monkeypatch.setattr(settings, "internal_service_token", TOKEN)
    monkeypatch.setattr(simulation_client, "_client", None)
    yield
    monkeypatch.setattr(simulation_client, "_client", None)


def _package_body() -> dict:
    return {
        "package": {
            "scene_id": str(SCENE_ID),
            "playthrough_id": str(uuid.uuid4()),
            "scene_type": "negotiation",
            "turn": 1,
            "situation": {"summary": "Talks."},
            "allowed_outcomes": [{"kind": "prose_only"}],
            "exchange_cap": 6,
            "default_outcome": {"kind": "prose_only"},
        },
        "status": "opened",
        "exchanges_remaining": 6,
    }


@respx.mock
async def test_fetch_sends_the_service_token_and_acting_user() -> None:
    route = respx.get(f"http://simulation.test{PACKAGE_URL}").respond(
        200, json=_package_body()
    )
    package = await simulation_client.fetch_scene_package(SCENE_ID, USER_ID)
    request = route.calls.last.request
    assert request.headers["x-internal-service-token"] == TOKEN
    assert request.headers["x-acting-user-id"] == str(USER_ID)
    assert package.package.exchange_cap == 6


@respx.mock
@pytest.mark.parametrize(
    ("status", "error"),
    [
        (404, SceneNotFoundError),
        (409, SceneNotOpenError),
        (500, SimulationUnavailableError),
    ],
)
async def test_error_statuses_map_to_domain_errors(status, error) -> None:
    respx.get(f"http://simulation.test{PACKAGE_URL}").respond(status, json={})
    with pytest.raises(error):
        await simulation_client.fetch_scene_package(SCENE_ID, USER_ID)


@respx.mock
async def test_network_failure_and_bad_bodies_are_unavailable() -> None:
    route = respx.get(f"http://simulation.test{PACKAGE_URL}")
    route.side_effect = httpx.ConnectError("refused")
    with pytest.raises(SimulationUnavailableError):
        await simulation_client.fetch_scene_package(SCENE_ID, USER_ID)
    route.side_effect = None
    route.respond(200, json={"unexpected": True})
    with pytest.raises(SimulationUnavailableError):
        await simulation_client.fetch_scene_package(SCENE_ID, USER_ID)


@respx.mock
async def test_submit_posts_the_exchange_and_parses_the_result() -> None:
    route = respx.post(f"http://simulation.test{EXCHANGE_URL}").respond(
        200,
        json={
            "status": "accepted",
            "scene_status": "opened",
            "exchanges_remaining": 5,
        },
    )
    submission = SceneExchangeSubmission.model_validate(
        {
            "sequence": 1,
            "player_text": "Peace?",
            "leader_text": "Perhaps.",
            "decision": {"action": "continue_talk"},
        }
    )
    result = await simulation_client.submit_exchange(SCENE_ID, USER_ID, submission)
    assert result.exchanges_remaining == 5
    assert b"Peace?" in route.calls.last.request.content
    assert route.calls.last.request.headers["content-type"] == "application/json"


@respx.mock
async def test_a_failure_report_is_posted_with_the_service_token() -> None:
    route = respx.post(
        f"http://simulation.test/internal/v1/scenes/{SCENE_ID}/failures"
    ).respond(
        200,
        json={
            "scene_status": "defaulted",
            "failed_attempts": 3,
            "attempts_remaining": 0,
        },
    )
    result = await simulation_client.report_scene_failure(SCENE_ID, USER_ID)
    request = route.calls.last.request
    assert request.headers["x-internal-service-token"] == TOKEN
    assert request.headers["x-acting-user-id"] == str(USER_ID)
    assert (result.scene_status.value, result.attempts_remaining) == ("defaulted", 0)


@respx.mock
async def test_store_letter_body_posts_the_text_with_the_service_token() -> None:
    route = respx.post(f"http://simulation.test/internal/v1/scenes/{SCENE_ID}/letter")
    route.respond(
        200,
        json={
            "status": "accepted",
            "scene_status": "pending",
            "exchanges_remaining": 1,
        },
    )

    result = await simulation_client.store_letter_body(
        SCENE_ID, USER_ID, "Dear Valdren"
    )

    request = route.calls.last.request
    assert request.headers["x-internal-service-token"] == TOKEN
    assert request.headers["x-acting-user-id"] == str(USER_ID)
    assert json.loads(request.content) == {"text": "Dear Valdren"}
    assert result.exchanges_remaining == 1

from uuid import uuid4

import respx
from httpx import AsyncClient
from tests.routers.test_campaign_after_ending import _start_ended_game
from tests.services.test_campaign_service import initialization

HEADERS = {"X-Internal-Service-Token": "internal"}


async def _running_game(api: AsyncClient) -> str:
    request = initialization().model_dump(mode="json")
    await api.post("/internal/v1/playthroughs", json=request, headers=HEADERS)
    return f"/v1/playthroughs/{request['playthrough_id']}"


async def test_epilogue_before_the_ending_is_a_conflict(api: AsyncClient) -> None:
    base = await _running_game(api)
    response = await api.get(f"{base}/epilogue")
    assert response.status_code == 409
    assert "epilogue_not_available" in response.text
    internal = "/internal" + base + "/epilogue/claim"
    claim = await api.post(internal, json={"claim_id": str(uuid4())}, headers=HEADERS)
    assert claim.status_code == 409


@respx.mock
async def test_epilogue_after_the_ending_starts_pending_and_is_owner_only(
    api: AsyncClient,
) -> None:
    base = await _start_ended_game(api)
    response = await api.get(f"{base}/epilogue")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"
    assert response.json()["narration"] is None
    assert (await api.get(f"/v1/playthroughs/{uuid4()}/epilogue")).status_code == 404


@respx.mock
async def test_internal_epilogue_routes_need_the_service_token(
    api: AsyncClient,
) -> None:
    base = await _start_ended_game(api)
    claim_path = "/internal" + base + "/epilogue/claim"
    body = {"claim_id": str(uuid4())}
    assert (await api.post(claim_path, json=body)).status_code == 401


@respx.mock
async def test_claim_then_complete_saves_the_entry_for_the_browser(
    api: AsyncClient,
) -> None:
    base = await _start_ended_game(api)
    outcome_text = respx.patch(url__regex=r".*/outcome-text$").respond(200)
    internal = "/internal" + base + "/epilogue"
    claim = await api.post(
        internal + "/claim", json={"claim_id": str(uuid4())}, headers=HEADERS
    )
    assert claim.status_code == 200
    assert claim.json()["briefing"]["ending_id"] == "default_defeat_capital_lost"
    completion = {
        "lease_token": claim.json()["lease_token"],
        "input_hash": claim.json()["input_hash"],
        "narration": "Chroniclers called it the year the capital fell.",
    }
    done = await api.post(internal + "/complete", json=completion, headers=HEADERS)
    assert done.status_code == 200
    assert done.json()["status"] == "completed"
    assert outcome_text.called
    assert completion["narration"] in outcome_text.calls.last.request.content.decode()
    public = (await api.get(f"{base}/epilogue")).json()
    assert public["narration"] == completion["narration"]
    assert "lease_token" not in public and "briefing" not in public


@respx.mock
async def test_a_failed_attempt_can_be_claimed_again(api: AsyncClient) -> None:
    base = await _start_ended_game(api)
    internal = "/internal" + base + "/epilogue"
    first = (
        await api.post(
            internal + "/claim", json={"claim_id": str(uuid4())}, headers=HEADERS
        )
    ).json()
    failed = await api.post(
        internal + "/fail",
        json={"lease_token": first["lease_token"], "error_code": "provider_timeout"},
        headers=HEADERS,
    )
    assert failed.json()["status"] == "failed"
    retry = await api.post(
        internal + "/claim", json={"claim_id": str(uuid4())}, headers=HEADERS
    )
    assert retry.status_code == 200
    assert retry.json()["lease_token"] != first["lease_token"]

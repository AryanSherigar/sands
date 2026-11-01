from uuid import uuid4

from httpx import AsyncClient
from psycopg import AsyncConnection
from tests.services.test_campaign_service import initialization

HEADERS = {"X-Internal-Service-Token": "internal"}


async def test_empty_summary_history_requires_owner_and_preserves_world(
    api: AsyncClient,
) -> None:
    request = initialization().model_dump(mode="json")
    response = await api.post(
        "/internal/v1/playthroughs", json=request, headers=HEADERS
    )
    assert response.status_code == 200
    base = f"/v1/playthroughs/{request['playthrough_id']}"
    before = (await api.get(f"{base}/world")).json()
    result = await api.get(f"{base}/summaries")
    assert result.status_code == 200
    assert result.json()["items"] == []
    assert (await api.get(f"{base}/world")).json() == before
    assert (await api.get(f"/v1/playthroughs/{uuid4()}/summaries")).status_code == 404


async def _pending(api: AsyncClient, connection: AsyncConnection) -> str:
    from uuid import UUID

    from app.repositories import summary_delivery_repo
    from app.services.summary_materialization import briefing_hash
    from strategy_contracts.summary import SummaryBriefing, SummaryFact

    request = initialization().model_dump(mode="json")
    await api.post("/internal/v1/playthroughs", json=request, headers=HEADERS)
    identity = UUID(request["playthrough_id"])
    summary = uuid4()
    package = SummaryBriefing(
        summary_id=summary,
        playthrough_id=identity,
        observer_faction_id="house_carrow",
        requested_turn=0,
        trigger="major_event",
        facts=[
            SummaryFact(
                event_id=uuid4(),
                kind="uprising_started",
                turn=0,
                text_key="uprising_started",
                region_ids=["carrow"],
            )
        ],
    )
    await summary_delivery_repo.insert(
        connection, package, "engine:1", briefing_hash(package)
    )
    return f"/v1/playthroughs/{identity}/summaries/{summary}"


async def test_claim_completion_retry_and_world_hash_are_independent(
    api, db_connection
):
    path = await _pending(api, db_connection)
    world_path = path.split("/summaries")[0] + "/world"
    before = (await api.get(world_path)).json()
    internal = "/internal" + path
    body = {"claim_id": str(uuid4())}
    assert (await api.post(internal + "/claim", json=body)).status_code == 401
    claim = await api.post(internal + "/claim", json=body, headers=HEADERS)
    assert claim.status_code == 200
    repeated = await api.post(internal + "/claim", json=body, headers=HEADERS)
    assert repeated.json()["lease_token"] == claim.json()["lease_token"]
    other = await api.post(
        internal + "/claim", json={"claim_id": str(uuid4())}, headers=HEADERS
    )
    assert other.status_code == 409
    completion = {
        "lease_token": claim.json()["lease_token"],
        "input_hash": claim.json()["input_hash"],
        "narration": "The realm rises in protest.",
    }
    result = await api.post(internal + "/complete", json=completion, headers=HEADERS)
    assert result.status_code == 200
    assert result.json()["status"] == "completed"
    assert (
        await api.post(internal + "/complete", json=completion, headers=HEADERS)
    ).json() == result.json()
    conflict = await api.post(
        internal + "/complete",
        json={**completion, "narration": "different"},
        headers=HEADERS,
    )
    assert conflict.status_code == 409
    assert (await api.get(path)).json()["narration"] == completion["narration"]
    after = (await api.get(world_path)).json()
    assert after["world_hash"] == before["world_hash"]
    assert after["world_version"] == before["world_version"]
    public = (await api.get(path)).json()
    assert "lease_token" not in public and "briefing" not in public


async def test_failed_delivery_reclaims_and_rejects_stale_completion(
    api, db_connection
):
    path = await _pending(api, db_connection)
    internal = "/internal" + path
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
    assert failed.status_code == 200 and failed.json()["is_retryable"]
    second = (
        await api.post(
            internal + "/claim", json={"claim_id": str(uuid4())}, headers=HEADERS
        )
    ).json()
    assert second["lease_token"] != first["lease_token"]
    stale = await api.post(
        internal + "/complete",
        json={
            "lease_token": first["lease_token"],
            "input_hash": first["input_hash"],
            "narration": "stale output",
        },
        headers=HEADERS,
    )
    assert stale.status_code == 409
    assert (await api.get(path)).json()["status"] == "generating"


async def test_scoped_cursor_and_foreign_request_are_not_visible(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    path = await _pending(api, db_connection)
    foreign = f"/v1/playthroughs/{uuid4()}/summaries/" + path.rsplit("/", 1)[1]
    assert (await api.get(foreign)).status_code == 404
    list_path = path.rsplit("/", 1)[0]
    assert (await api.get(list_path + "?after_id=" + str(uuid4()))).status_code == 404
    assert (await api.get(list_path + "?limit=51")).status_code == 422

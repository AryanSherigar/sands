from uuid import UUID, uuid4

from app.repositories import dispatch_delivery_repo
from httpx import AsyncClient
from psycopg import AsyncConnection
from strategy_contracts.agents import (
    MAX_DISPATCH_PROSE_CHARS,
    AgentTrait,
    AgentView,
    DispatchBriefing,
)
from strategy_contracts.pressure import PressureBand, RumorTopic
from tests.services.art_helpers import seed_campaign

HEADERS = {"X-Internal-Service-Token": "internal"}
NARRATION = "My lord, the border is quiet."


async def _seed(connection: AsyncConnection) -> UUID:
    identity = await seed_campaign(connection)
    await dispatch_delivery_repo.insert(
        connection,
        DispatchBriefing(
            rumor_id="rumor_1",
            playthrough_id=identity,
            turn=3,
            agent=AgentView(name="Aldous", traits=[AgentTrait.HONEST]),
            about_faction_id="house_dunwick",
            topic=RumorTopic.WILL,
            reported_band=PressureBand.HIGH,
        ),
    )
    return identity


def _path(identity: UUID, action: str, rumor_id: str = "rumor_1") -> str:
    return f"/internal/v1/playthroughs/{identity}/dispatches/{rumor_id}/{action}"


async def test_missing_service_token_is_rejected(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await _seed(db_connection)

    response = await api.post(_path(identity, "claim"), json={"claim_id": str(uuid4())})

    assert response.status_code in (401, 403)


async def test_claim_complete_round_trip_and_public_read(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await _seed(db_connection)
    claim = await api.post(
        _path(identity, "claim"), json={"claim_id": str(uuid4())}, headers=HEADERS
    )
    assert claim.status_code == 200
    assert claim.json()["briefing"]["reported_band"] == "high"

    done = await api.post(
        _path(identity, "complete"),
        json={"lease_token": claim.json()["lease_token"], "narration": NARRATION},
        headers=HEADERS,
    )
    public = await api.get(f"/v1/playthroughs/{identity}/dispatches/rumor_1")

    assert done.status_code == 200 and done.json()["status"] == "completed"
    assert public.json()["narration"] == NARRATION


async def test_second_claim_is_409_and_overlong_narration_is_422(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await _seed(db_connection)
    first = await api.post(
        _path(identity, "claim"), json={"claim_id": str(uuid4())}, headers=HEADERS
    )
    second = await api.post(
        _path(identity, "claim"), json={"claim_id": str(uuid4())}, headers=HEADERS
    )
    too_long = await api.post(
        _path(identity, "complete"),
        json={
            "lease_token": first.json()["lease_token"],
            "narration": "x" * (MAX_DISPATCH_PROSE_CHARS + 1),
        },
        headers=HEADERS,
    )

    assert second.status_code == 409
    assert too_long.status_code == 422


async def test_fail_route_records_failure(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await _seed(db_connection)
    claim = await api.post(
        _path(identity, "claim"), json={"claim_id": str(uuid4())}, headers=HEADERS
    )

    failed = await api.post(
        _path(identity, "fail"),
        json={
            "lease_token": claim.json()["lease_token"],
            "error_code": "provider_timeout",
        },
        headers=HEADERS,
    )

    assert failed.status_code == 200 and failed.json()["status"] == "failed"

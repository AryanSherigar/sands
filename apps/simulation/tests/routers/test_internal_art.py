from uuid import uuid4

from httpx import AsyncClient
from psycopg import AsyncConnection
from tests.services.art_helpers import EVENT_ID, add_pending_event, seed_campaign

HEADERS = {"X-Internal-Service-Token": "internal"}
ART_URL = "https://cdn.example/strategy-art/one.webp"


def _path(identity: object, action: str) -> str:
    return f"/internal/v1/playthroughs/{identity}/art/event/{EVENT_ID}/{action}"


async def test_claim_requires_service_token(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await seed_campaign(db_connection)
    response = await api.post(_path(identity, "claim"), json={"claim_id": str(uuid4())})
    assert response.status_code in (401, 403)


async def test_claim_complete_round_trip(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    identity = await seed_campaign(db_connection)
    await add_pending_event(db_connection, identity)
    claim = await api.post(
        _path(identity, "claim"), json={"claim_id": str(uuid4())}, headers=HEADERS
    )
    assert claim.status_code == 200
    lease = claim.json()["lease_token"]
    done = await api.post(
        _path(identity, "complete"),
        json={"lease_token": lease, "art_url": ART_URL},
        headers=HEADERS,
    )
    assert done.status_code == 200
    assert done.json()["art_url"] == ART_URL

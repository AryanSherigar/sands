from uuid import UUID, uuid4

from app.repositories import dispatch_delivery_repo
from httpx import AsyncClient
from psycopg import AsyncConnection
from strategy_contracts.agents import AgentTrait, AgentView, DispatchBriefing
from strategy_contracts.pressure import PressureBand, RumorTopic
from tests.middleware.helpers import make_token
from tests.services.test_campaign_service import initialization

HEADERS = {"X-Internal-Service-Token": "internal"}
STRANGER = {"Authorization": f"Bearer {make_token(sub=str(uuid4()))}"}


async def _seed(api: AsyncClient, connection: AsyncConnection) -> tuple[str, UUID]:
    request = initialization().model_dump(mode="json")
    await api.post("/internal/v1/playthroughs", json=request, headers=HEADERS)
    identity = UUID(request["playthrough_id"])
    for rumor_id, turn in (("rumor_1", 2), ("rumor_2", 5)):
        await dispatch_delivery_repo.insert(
            connection,
            DispatchBriefing(
                rumor_id=rumor_id,
                playthrough_id=identity,
                turn=turn,
                agent=AgentView(name="Aldous", traits=[AgentTrait.HONEST]),
                about_faction_id="house_dunwick",
                topic=RumorTopic.WILL,
                reported_band=PressureBand.HIGH,
            ),
        )
    return f"/v1/playthroughs/{identity}/dispatches", identity


async def test_list_returns_newest_first_without_internal_fields(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    path, _ = await _seed(api, db_connection)

    response = await api.get(path)

    assert response.status_code == 200
    items = response.json()
    assert [item["rumor_id"] for item in items] == ["rumor_2", "rumor_1"]
    assert items[0]["fallback_line_key"] == "will.high"
    assert items[0]["status"] == "pending"
    assert not {"briefing", "lease_token", "attempts"} & set(items[0])


async def test_get_one_dispatch(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    path, _ = await _seed(api, db_connection)

    response = await api.get(f"{path}/rumor_1")

    assert response.status_code == 200
    assert response.json()["agent"] == {"name": "Aldous", "traits": ["honest"]}


async def test_unknown_rumor_is_404(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    path, _ = await _seed(api, db_connection)

    assert (await api.get(f"{path}/rumor_9")).status_code == 404


async def test_other_users_playthrough_is_404(
    api: AsyncClient, db_connection: AsyncConnection
) -> None:
    path, _ = await _seed(api, db_connection)

    assert (await api.get(path, headers=STRANGER)).status_code == 404
    assert (await api.get(f"{path}/rumor_1", headers=STRANGER)).status_code == 404

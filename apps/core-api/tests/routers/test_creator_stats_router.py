import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import add_playthrough, make_scenario, make_user


def auth(user_id: uuid.UUID) -> dict[str, str]:
    return {"x-dev-user-id": str(user_id)}


@pytest.mark.asyncio
async def test_owner_gets_scenario_stats(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    for _ in range(5):
        await add_playthrough(db_session, scenario, alice, turn_count=3)
    await add_playthrough(db_session, scenario, creator, is_playtest=True)

    response = await async_client.get(
        f"/v1/scenarios/{scenario.scenario_id}/stats?range=7d",
        headers=auth(creator.user_id),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stats_range"] == "7d"
    assert body["bucket"] == "day"
    assert body["plays"]["total_plays"] == 5
    assert body["is_sample_sufficient"] is True
    assert body["outcomes"] is not None
    assert body["versions"][0]["scenario_version"] == 1
    assert body["versions"][0]["plays"] == 5
    assert body["heatmap"] == []
    assert body["outcomes"]["end_conditions"] == []
    assert "benchmarks" in body


@pytest.mark.asyncio
async def test_non_owner_and_missing_scenario_get_404(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    creator = await make_user(db_session, "Creator")
    stranger = await make_user(db_session, "Stranger")
    scenario = await make_scenario(db_session, creator)

    foreign = await async_client.get(
        f"/v1/scenarios/{scenario.scenario_id}/stats", headers=auth(stranger.user_id)
    )
    missing = await async_client.get(
        f"/v1/scenarios/{uuid.uuid4()}/stats", headers=auth(creator.user_id)
    )

    assert foreign.status_code == 404
    assert missing.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_requests_get_401(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    creator = await make_user(db_session, "Creator")
    scenario = await make_scenario(db_session, creator)

    overview = await async_client.get("/v1/creators/me/stats")
    deep = await async_client.get(f"/v1/scenarios/{scenario.scenario_id}/stats")

    assert overview.status_code == 401
    assert deep.status_code == 401


@pytest.mark.asyncio
async def test_invalid_range_returns_422(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    creator = await make_user(db_session, "Creator")
    response = await async_client.get(
        "/v1/creators/me/stats?range=365d", headers=auth(creator.user_id)
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_overview_defaults_to_30d(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    creator = await make_user(db_session, "Creator")
    alice = await make_user(db_session, "Alice")
    scenario = await make_scenario(db_session, creator)
    await add_playthrough(db_session, scenario, alice)

    response = await async_client.get(
        "/v1/creators/me/stats", headers=auth(creator.user_id)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["stats_range"] == "30d"
    assert body["has_published_scenarios"] is True
    assert body["scenarios"][0]["plays"] == 1
    assert body["sample_threshold"] == 5

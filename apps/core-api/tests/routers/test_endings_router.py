import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import add_playthrough, make_scenario, make_user


@pytest.mark.asyncio
async def test_endings_requires_auth(async_client: AsyncClient) -> None:
    assert (await async_client.get("/v1/users/me/endings")).status_code == 401


@pytest.mark.asyncio
async def test_endings_empty_shape(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    user = await make_user(db_session)
    response = await async_client.get(
        "/v1/users/me/endings", headers={"x-dev-user-id": str(user.user_id)}
    )
    assert response.status_code == 200
    assert response.json() == {"scenarios": []}


@pytest.mark.asyncio
async def test_endings_owner_only_data_and_no_visitor_route(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    me = await make_user(db_session, "Me")
    other = await make_user(db_session, "Other")
    scenario = await make_scenario(db_session, me, mode="master")
    condition_id = uuid.uuid4()
    snap = {
        "end_conditions": [
            {
                "outcome_title": "Ashen",
                "outcome_tag": "win",
                "is_secret": False,
                "priority": 0,
                "end_condition_id": str(condition_id),
            }
        ]
    }
    await add_playthrough(
        db_session,
        scenario,
        me,
        turn_count=5,
        status="completed",
        outcome_tag="win",
        outcome_title="Ashen",
        outcome_id=condition_id,
        snapshot=snap,
    )
    await add_playthrough(db_session, scenario, other, turn_count=5, snapshot=snap)
    headers = {"x-dev-user-id": str(me.user_id)}

    body = (await async_client.get("/v1/users/me/endings", headers=headers)).json()
    assert body["scenarios"][0]["found_count"] == 1
    assert body["scenarios"][0]["slots"] == [
        {"is_found": True, "title": "Ashen", "outcome_tag": "win"}
    ]

    other_view = (
        await async_client.get(
            "/v1/users/me/endings", headers={"x-dev-user-id": str(other.user_id)}
        )
    ).json()
    assert other_view["scenarios"][0]["found_count"] == 0
    assert other_view["scenarios"][0]["slots"] == [
        {"is_found": False, "title": None, "outcome_tag": None}
    ]

    visitor = await async_client.get(
        f"/v1/users/{uuid.uuid4()}/endings", headers=headers
    )
    assert visitor.status_code == 404

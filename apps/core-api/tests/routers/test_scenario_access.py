"""Single-use invite links and the private-scenario allowlist endpoints."""

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from app.config import settings
from app.db.models.scenario_invite import ScenarioInvite
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.scenario_repo import ScenarioRepo
from app.services.scenario_access import ScenarioAccessChecker
from httpx import AsyncClient
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from tests.routers.test_private_scenarios import as_user, make_scenario, make_user

INVITE_URL_PREFIX = f"{settings.frontend_base_url}/invite/"


@pytest.fixture
async def creator(db_session: AsyncSession):
    return await make_user(db_session, "Creator")


@pytest.fixture
async def guest(db_session: AsyncSession):
    return await make_user(db_session, "Guest")


@pytest.fixture
async def second_guest(db_session: AsyncSession):
    return await make_user(db_session, "Second Guest")


@pytest.fixture
async def scenario(db_session: AsyncSession, creator):
    return await make_scenario(db_session, creator, "Private Tale")


async def _create_token(async_client: AsyncClient, scenario, creator) -> str:
    response = await async_client.post(
        f"/v1/scenarios/{scenario.scenario_id}/invites", headers=as_user(creator)
    )
    assert response.status_code == 201
    url = response.json()["url"]
    assert url.startswith(INVITE_URL_PREFIX)
    return url.removeprefix(INVITE_URL_PREFIX)


async def _can_open(db_session: AsyncSession, scenario, user) -> bool:
    stored = await ScenarioRepo(db_session).get_by_id(scenario.scenario_id)
    checker = ScenarioAccessChecker(ScenarioAccessRepo(db_session))
    return await checker.can_open(stored, user.user_id)


@pytest.mark.asyncio
async def test_owner_creates_an_invite_and_only_its_hash_is_stored(
    async_client: AsyncClient, db_session: AsyncSession, scenario, creator
):
    response = await async_client.post(
        f"/v1/scenarios/{scenario.scenario_id}/invites", headers=as_user(creator)
    )

    assert response.status_code == 201
    body = response.json()
    token = body["url"].removeprefix(INVITE_URL_PREFIX)
    expires_at = datetime.fromisoformat(body["expires_at"])
    assert expires_at > datetime.now(UTC) + timedelta(days=6)
    stored = (await db_session.execute(select(ScenarioInvite))).scalars().one()
    assert stored.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert token not in stored.token_hash
    assert stored.created_by == creator.user_id
    assert stored.consumed_at is None


@pytest.mark.asyncio
async def test_a_non_owner_cannot_create_an_invite(
    async_client: AsyncClient, scenario, guest
):
    response = await async_client.post(
        f"/v1/scenarios/{scenario.scenario_id}/invites", headers=as_user(guest)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_accepting_an_invite_grants_access_and_burns_the_token(
    async_client: AsyncClient,
    db_session: AsyncSession,
    scenario,
    creator,
    guest,
    second_guest,
):
    token = await _create_token(async_client, scenario, creator)
    assert not await _can_open(db_session, scenario, guest)

    accepted = await async_client.post(
        f"/v1/invites/{token}/accept", headers=as_user(guest)
    )

    assert accepted.status_code == 200
    assert accepted.json() == {"scenario_id": str(scenario.scenario_id)}
    assert await _can_open(db_session, scenario, guest)
    reused = await async_client.post(
        f"/v1/invites/{token}/accept", headers=as_user(second_guest)
    )
    assert reused.status_code == 410
    assert not await _can_open(db_session, scenario, second_guest)


@pytest.mark.asyncio
async def test_an_unknown_token_is_not_found(async_client: AsyncClient, guest):
    response = await async_client.post(
        "/v1/invites/not-a-real-token/accept", headers=as_user(guest)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_an_expired_invite_is_gone(
    async_client: AsyncClient, db_session: AsyncSession, scenario, creator, guest
):
    token = await _create_token(async_client, scenario, creator)
    await db_session.execute(
        update(ScenarioInvite).values(expires_at=datetime.now(UTC) - timedelta(days=1))
    )

    response = await async_client.post(
        f"/v1/invites/{token}/accept", headers=as_user(guest)
    )

    assert response.status_code == 410
    assert not await _can_open(db_session, scenario, guest)


@pytest.mark.asyncio
async def test_the_owner_opening_their_own_link_does_not_burn_it(
    async_client: AsyncClient, db_session: AsyncSession, scenario, creator, guest
):
    token = await _create_token(async_client, scenario, creator)

    own = await async_client.post(
        f"/v1/invites/{token}/accept", headers=as_user(creator)
    )
    later = await async_client.post(
        f"/v1/invites/{token}/accept", headers=as_user(guest)
    )

    assert own.status_code == 200
    assert later.status_code == 200
    assert await _can_open(db_session, scenario, guest)


@pytest.mark.asyncio
async def test_accepting_requires_sign_in(async_client: AsyncClient):
    response = await async_client.post("/v1/invites/anything/accept")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_owner_lists_and_removes_people_with_access(
    async_client: AsyncClient, db_session: AsyncSession, scenario, creator, guest
):
    token = await _create_token(async_client, scenario, creator)
    await async_client.post(f"/v1/invites/{token}/accept", headers=as_user(guest))

    listed = await async_client.get(
        f"/v1/scenarios/{scenario.scenario_id}/access", headers=as_user(creator)
    )
    assert listed.status_code == 200
    assert listed.json() == [{"user_id": str(guest.user_id), "display_name": "Guest"}]

    removed = await async_client.delete(
        f"/v1/scenarios/{scenario.scenario_id}/access/{guest.user_id}",
        headers=as_user(creator),
    )
    assert removed.status_code == 204
    assert not await _can_open(db_session, scenario, guest)
    relisted = await async_client.get(
        f"/v1/scenarios/{scenario.scenario_id}/access", headers=as_user(creator)
    )
    assert relisted.json() == []


@pytest.mark.asyncio
async def test_a_non_owner_cannot_list_or_remove_access(
    async_client: AsyncClient, scenario, guest, second_guest
):
    listed = await async_client.get(
        f"/v1/scenarios/{scenario.scenario_id}/access", headers=as_user(guest)
    )
    removed = await async_client.delete(
        f"/v1/scenarios/{scenario.scenario_id}/access/{second_guest.user_id}",
        headers=as_user(guest),
    )

    assert listed.status_code == 404
    assert removed.status_code == 404

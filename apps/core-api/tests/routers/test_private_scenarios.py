"""A private scenario is open to its creator and the allowlist, and to no one else."""

import uuid
from datetime import UTC, datetime

import pytest
from app.db.models.scenario import Scenario
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from app.repositories.user_repo import UserRepo
from sqlalchemy.ext.asyncio import AsyncSession

NOT_FOUND = 404


async def make_user(db_session: AsyncSession, name: str):
    return await UserRepo(db_session).create(f"uid-{uuid.uuid4()}", name)


def as_user(user) -> dict[str, str]:
    return {"x-dev-user-id": str(user.user_id)}


async def make_scenario(
    db_session: AsyncSession, creator, title: str, visibility: str = "private"
) -> Scenario:
    scenario = Scenario(
        creator_id=creator.user_id,
        title=title,
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
        published_at=datetime.now(UTC),
        visibility=visibility,
        narrator_persona="A narrator.",
        world_data={"lore": "Lore."},
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


@pytest.fixture
async def creator(db_session: AsyncSession):
    return await make_user(db_session, "Creator")


@pytest.fixture
async def outsider(db_session: AsyncSession):
    return await make_user(db_session, "Outsider")


@pytest.fixture
async def guest(db_session: AsyncSession):
    return await make_user(db_session, "Guest")


@pytest.fixture
async def private_scenario(db_session, creator, guest) -> Scenario:
    scenario = await make_scenario(db_session, creator, "Hidden Tale")
    await ScenarioAccessRepo(db_session).add(scenario.scenario_id, guest.user_id)
    return scenario


@pytest.fixture
async def public_scenario(db_session, creator) -> Scenario:
    return await make_scenario(db_session, creator, "Open Tale", "public")


def path(scenario: Scenario, suffix: str = "") -> str:
    return f"/v1/scenarios/{scenario.scenario_id}{suffix}"


def create_body(scenario: Scenario) -> dict[str, object]:
    return {"scenario_id": str(scenario.scenario_id), "setup_values": {}}


async def test_the_creator_and_an_allowed_user_can_open_it(
    async_client, creator, guest, private_scenario
):
    for user in (creator, guest):
        response = await async_client.get(path(private_scenario), headers=as_user(user))
        assert response.status_code == 200
        assert response.json()["visibility"] == "private"


async def test_everyone_else_gets_not_found_and_cannot_tell_it_exists(
    async_client, outsider, private_scenario
):
    missing = await async_client.get(path(private_scenario), headers=as_user(outsider))
    anonymous = await async_client.get(path(private_scenario))
    unknown = await async_client.get(
        f"/v1/scenarios/{uuid.uuid4()}", headers=as_user(outsider)
    )
    assert (
        missing.status_code == anonymous.status_code == unknown.status_code == NOT_FOUND
    )
    assert missing.json() == unknown.json()


async def test_a_public_scenario_is_unaffected(async_client, outsider, public_scenario):
    response = await async_client.get(path(public_scenario), headers=as_user(outsider))
    assert response.status_code == 200
    assert response.json()["visibility"] == "public"


async def test_discovery_never_lists_a_private_scenario(
    async_client, creator, guest, outsider, private_scenario, public_scenario
):
    for user in (creator, guest, outsider):
        response = await async_client.get("/v1/scenarios", headers=as_user(user))
        titles = [item["title"] for item in response.json()["items"]]
        assert "Open Tale" in titles
        assert "Hidden Tale" not in titles


async def test_the_creator_sees_it_in_their_own_list(
    async_client, creator, outsider, private_scenario
):
    mine = await async_client.get("/v1/scenarios?mine=true", headers=as_user(creator))
    assert "Hidden Tale" in [item["title"] for item in mine.json()["items"]]
    theirs = await async_client.get(
        "/v1/scenarios?mine=true", headers=as_user(outsider)
    )
    assert "Hidden Tale" not in [item["title"] for item in theirs.json()["items"]]


async def test_an_allowed_user_can_bookmark_it_and_sees_it_in_saved(
    async_client, guest, private_scenario
):
    marked = await async_client.post(
        path(private_scenario, "/bookmark"), headers=as_user(guest)
    )
    assert marked.status_code == 200
    saved = await async_client.get("/v1/scenarios?saved=true", headers=as_user(guest))
    assert "Hidden Tale" in [item["title"] for item in saved.json()["items"]]


async def test_an_outsider_cannot_bookmark_review_or_read_anything_about_it(
    async_client, outsider, private_scenario
):
    headers = as_user(outsider)
    attempts = [
        await async_client.post(path(private_scenario, "/bookmark"), headers=headers),
        await async_client.get(path(private_scenario, "/reviews"), headers=headers),
        await async_client.post(
            path(private_scenario, "/reviews"),
            json={"rating": 5, "comment": "Great"},
            headers=headers,
        ),
        await async_client.get(
            path(private_scenario, "/playthroughs"), headers=headers
        ),
        await async_client.get(path(private_scenario, "/endings"), headers=headers),
    ]
    assert [item.status_code for item in attempts] == [NOT_FOUND] * 5


async def test_an_allowed_user_can_read_its_reviews_playthroughs_and_endings(
    async_client, guest, private_scenario
):
    headers = as_user(guest)
    for suffix in ("/reviews", "/playthroughs", "/endings"):
        response = await async_client.get(
            path(private_scenario, suffix), headers=headers
        )
        assert response.status_code == 200


async def test_only_the_creator_and_allowed_users_can_start_a_run(
    async_client, creator, guest, outsider, private_scenario
):
    for user in (creator, guest):
        response = await async_client.post(
            "/v1/playthroughs",
            json=create_body(private_scenario),
            headers=as_user(user),
        )
        assert response.status_code == 201
    refused = await async_client.post(
        "/v1/playthroughs",
        json=create_body(private_scenario),
        headers=as_user(outsider),
    )
    assert refused.status_code == NOT_FOUND


async def test_a_run_of_a_private_scenario_pins_its_visibility_and_cannot_be_shared(
    async_client, creator, private_scenario
):
    created = await async_client.post(
        "/v1/playthroughs", json=create_body(private_scenario), headers=as_user(creator)
    )
    playthrough_id = created.json()["playthrough_id"]

    shared = await async_client.post(
        f"/v1/playthroughs/{playthrough_id}/share",
        json={"mode": "spectate"},
        headers=as_user(creator),
    )

    assert shared.status_code == 403


async def test_a_run_of_a_public_scenario_can_still_be_shared(
    async_client, creator, public_scenario
):
    created = await async_client.post(
        "/v1/playthroughs", json=create_body(public_scenario), headers=as_user(creator)
    )
    shared = await async_client.post(
        f"/v1/playthroughs/{created.json()['playthrough_id']}/share",
        json={"mode": "spectate"},
        headers=as_user(creator),
    )
    assert shared.status_code == 201

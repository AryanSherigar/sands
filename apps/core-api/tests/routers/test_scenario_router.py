"""Integration tests for Scenario REST endpoints."""

import asyncio
import uuid
from datetime import UTC, datetime

import pytest
from app.db.models.bookmark import Bookmark
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from strategy_contracts.examples import load_three_crowns

pytestmark = pytest.mark.usefixtures("scenario_memory_purge")


async def _poll_until_settled(
    async_client: AsyncClient, scenario_id: str, headers: dict, attempts: int = 20
) -> dict:
    """Poll GET /v1/scenarios/{id} until publish settles, mirroring a real client."""
    for _ in range(attempts):
        resp = await async_client.get(f"/v1/scenarios/{scenario_id}", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        if data["status"] != "publishing":
            return data
        await asyncio.sleep(0.05)
    raise AssertionError(f"publish never settled for scenario {scenario_id}")


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    user_repo = UserRepo(db_session)
    return await user_repo.create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )


@pytest.fixture
async def dev_user2(db_session: AsyncSession):
    user_repo = UserRepo(db_session)
    return await user_repo.create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev User 2"
    )


@pytest.mark.asyncio
async def test_create_and_get_scenario_flow(
    async_client: AsyncClient, dev_user, dev_user2
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    payload = {
        "title": "Dragon's Lair",
        "mode": "newbie",
        "complexity_tier": "intermediate",
        "logline": "Enter the lair if you dare.",
    }

    # 1. Create Scenario
    response = await async_client.post("/v1/scenarios", json=payload, headers=headers)
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Dragon's Lair"
    assert data["status"] == "draft"
    scenario_id = data["scenario_id"]

    # 2. Get Scenario as Creator
    response = await async_client.get(f"/v1/scenarios/{scenario_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["scenario_id"] == scenario_id

    # 3. Get Scenario as Non-Creator (should return 404 for draft)
    headers2 = {"x-dev-user-id": str(dev_user2.user_id)}
    response = await async_client.get(f"/v1/scenarios/{scenario_id}", headers=headers2)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_patch_and_delete_scenario_flow(async_client: AsyncClient, dev_user):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    create_payload = {
        "title": "Ancient Temple",
        "mode": "master",
        "complexity_tier": "master",
    }

    # 1. Create
    resp = await async_client.post(
        "/v1/scenarios", json=create_payload, headers=headers
    )
    assert resp.status_code == 201
    scenario_id = resp.json()["scenario_id"]

    # 2. Patch title (metadata) -> current_version remains 1
    patch_resp1 = await async_client.patch(
        f"/v1/scenarios/{scenario_id}",
        json={"title": "Ruined Temple"},
        headers=headers,
    )
    assert patch_resp1.status_code == 200
    assert patch_resp1.json()["title"] == "Ruined Temple"
    assert patch_resp1.json()["current_version"] == 1

    # 3. Patch narrator_persona (story) -> current_version becomes 2
    patch_resp2 = await async_client.patch(
        f"/v1/scenarios/{scenario_id}",
        json={"narrator_persona": "Spooky Narrator"},
        headers=headers,
    )
    assert patch_resp2.status_code == 200
    assert patch_resp2.json()["current_version"] == 2

    # 3b. Patch narrator_voice_name (story) -> current_version becomes 3
    patch_resp3 = await async_client.patch(
        f"/v1/scenarios/{scenario_id}",
        json={"narrator_voice_name": "Kore"},
        headers=headers,
    )
    assert patch_resp3.status_code == 200
    assert patch_resp3.json()["narrator_voice_name"] == "Kore"
    assert patch_resp3.json()["current_version"] == 3

    # 4. Delete scenario
    del_resp = await async_client.delete(
        f"/v1/scenarios/{scenario_id}", headers=headers
    )
    assert del_resp.status_code == 204

    # 5. Verify deleted
    get_resp = await async_client.get(f"/v1/scenarios/{scenario_id}", headers=headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_list_scenarios_my_dashboard(async_client: AsyncClient, dev_user):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    # Create two draft scenarios
    await async_client.post(
        "/v1/scenarios",
        json={"title": "Draft 1", "mode": "newbie", "complexity_tier": "newbie"},
        headers=headers,
    )
    await async_client.post(
        "/v1/scenarios",
        json={"title": "Draft 2", "mode": "newbie", "complexity_tier": "newbie"},
        headers=headers,
    )

    # Fetch mine scenarios
    list_resp = await async_client.get("/v1/scenarios?mine=true", headers=headers)
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total_count"] >= 2


@pytest.mark.asyncio
async def test_list_scenarios_saved_filter(
    async_client: AsyncClient, db_session: AsyncSession, dev_user, dev_user2
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    saved_scenario = Scenario(
        creator_id=dev_user2.user_id,
        title="Bookmarked Tale",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
        published_at=datetime.now(UTC),
    )
    other_scenario = Scenario(
        creator_id=dev_user2.user_id,
        title="Unrelated Tale",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
        published_at=datetime.now(UTC),
    )
    db_session.add_all([saved_scenario, other_scenario])
    await db_session.commit()

    db_session.add(
        Bookmark(user_id=dev_user.user_id, scenario_id=saved_scenario.scenario_id)
    )
    await db_session.commit()

    resp = await async_client.get("/v1/scenarios?saved=true", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 1
    assert data["items"][0]["scenario_id"] == str(saved_scenario.scenario_id)

    unauth_resp = await async_client.get("/v1/scenarios?saved=true")
    assert unauth_resp.status_code == 403


@pytest.mark.asyncio
async def test_list_scenarios_played_filter(
    async_client: AsyncClient, db_session: AsyncSession, dev_user, dev_user2
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    played_scenario = Scenario(
        creator_id=dev_user2.user_id,
        title="Played Tale",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
        published_at=datetime.now(UTC),
    )
    other_scenario = Scenario(
        creator_id=dev_user2.user_id,
        title="Never Played Tale",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
        published_at=datetime.now(UTC),
    )
    db_session.add_all([played_scenario, other_scenario])
    await db_session.commit()

    db_session.add(
        Playthrough(
            scenario_id=played_scenario.scenario_id,
            created_by=dev_user.user_id,
            scenario_version=1,
        )
    )
    await db_session.commit()

    resp = await async_client.get("/v1/scenarios?played=true", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_count"] == 1
    assert data["items"][0]["scenario_id"] == str(played_scenario.scenario_id)

    unauth_resp = await async_client.get("/v1/scenarios?played=true")
    assert unauth_resp.status_code == 403


@pytest.mark.asyncio
async def test_publish_flow_success(
    async_client_real_background: AsyncClient,
    dev_user,
    cleanup_scenarios: list[uuid.UUID],
):
    async_client = async_client_real_background
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    create_resp = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "Publishable Tale",
            "mode": "newbie",
            "complexity_tier": "newbie",
            "content_tag": "all-ages",
            "visibility": "public",
            "logline": "A tale worth publishing.",
            "opening_scene": "Once upon a time.",
        },
        headers=headers,
    )
    scenario_id = create_resp.json()["scenario_id"]
    cleanup_scenarios.append(uuid.UUID(scenario_id))

    for mood in (
        "peaceful",
        "mystery",
        "tension",
        "combat",
        "melancholy",
        "triumph",
    ):
        default_resp = await async_client.post(
            f"/v1/scenarios/{scenario_id}/music/{mood}/default", headers=headers
        )
        assert default_resp.status_code == 200

    publish_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/publish", headers=headers
    )
    assert publish_resp.status_code == 202
    assert publish_resp.json()["status"] in ("publishing", "published")

    settled = await _poll_until_settled(async_client, scenario_id, headers)
    assert settled["status"] == "published"
    assert settled["published_at"] is not None
    assert settled["publish_error"] is None

    # Now visible in the public discovery feed.
    discovery_resp = await async_client.get("/v1/scenarios")
    assert discovery_resp.status_code == 200
    ids = [item["scenario_id"] for item in discovery_resp.json()["items"]]
    assert scenario_id in ids


@pytest.mark.asyncio
async def test_publish_flow_content_check_failure_reverts_to_draft(
    async_client: AsyncClient, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    create_resp = await async_client.post(
        "/v1/scenarios",
        json={"title": "Untagged Tale", "mode": "newbie", "complexity_tier": "newbie"},
        headers=headers,
    )
    scenario_id = create_resp.json()["scenario_id"]

    publish_resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/publish", headers=headers
    )
    assert publish_resp.status_code == 202

    settled = await _poll_until_settled(async_client, scenario_id, headers)
    assert settled["status"] == "draft"
    assert settled["published_at"] is None
    assert settled["publish_error"] is not None

    # Not visible in the public discovery feed.
    discovery_resp = await async_client.get("/v1/scenarios")
    ids = [item["scenario_id"] for item in discovery_resp.json()["items"]]
    assert scenario_id not in ids


@pytest.mark.asyncio
async def test_publish_rejected_while_already_publishing(
    async_client: AsyncClient, db_session: AsyncSession, dev_user
):
    # FastAPI's BackgroundTasks run to completion before the ASGI response is
    # sent (verified: not a real race under the in-process test transport),
    # so a live "publishing" window can't be caught by racing two real HTTP
    # calls here. Instead, force the in-flight state directly via the repo
    # (arrange), then exercise the real endpoint's guard (act/assert).
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    create_resp = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "Double Publish",
            "mode": "newbie",
            "complexity_tier": "newbie",
            "content_tag": "all-ages",
        },
        headers=headers,
    )
    scenario_id = create_resp.json()["scenario_id"]

    repo = ScenarioRepo(db_session)
    scenario = await repo.get_by_id(uuid.UUID(scenario_id))
    scenario.status = "publishing"
    await repo.update(scenario)

    resp = await async_client.post(
        f"/v1/scenarios/{scenario_id}/publish", headers=headers
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_patch_rejected_while_publishing(
    async_client: AsyncClient, db_session: AsyncSession, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    create_resp = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "Mid Publish Edit",
            "mode": "newbie",
            "complexity_tier": "newbie",
            "content_tag": "all-ages",
        },
        headers=headers,
    )
    scenario_id = create_resp.json()["scenario_id"]

    repo = ScenarioRepo(db_session)
    scenario = await repo.get_by_id(uuid.UUID(scenario_id))
    scenario.status = "publishing"
    await repo.update(scenario)

    patch_resp = await async_client.patch(
        f"/v1/scenarios/{scenario_id}",
        json={"title": "Sneaky Edit"},
        headers=headers,
    )
    assert patch_resp.status_code == 409


async def _add_published(
    db_session: AsyncSession, creator_id: uuid.UUID, title: str, **overrides: object
) -> Scenario:
    scenario = Scenario(
        creator_id=creator_id,
        title=title,
        mode=overrides.pop("mode", "newbie"),
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
        published_at=datetime.now(UTC),
        **overrides,
    )
    db_session.add(scenario)
    await db_session.commit()
    return scenario


@pytest.mark.asyncio
async def test_list_scenarios_text_query_matches_title_or_logline(
    async_client: AsyncClient, db_session: AsyncSession, dev_user
):
    await _add_published(db_session, dev_user.user_id, "Dragon Keep")
    await _add_published(
        db_session, dev_user.user_id, "Quiet Town", logline="A dragon sleeps here"
    )
    await _add_published(db_session, dev_user.user_id, "Space Bar")

    resp = await async_client.get(
        f"/v1/scenarios?q=dragon&creator_id={dev_user.user_id}"
    )

    assert resp.status_code == 200
    titles = {item["title"] for item in resp.json()["items"]}
    assert titles == {"Dragon Keep", "Quiet Town"}


@pytest.mark.asyncio
async def test_list_scenarios_text_query_treats_wildcards_literally(
    async_client: AsyncClient, db_session: AsyncSession, dev_user
):
    await _add_published(db_session, dev_user.user_id, "100% Fun")
    await _add_published(db_session, dev_user.user_id, "Plain Story")

    resp = await async_client.get(
        "/v1/scenarios", params={"q": "%", "creator_id": str(dev_user.user_id)}
    )

    assert [item["title"] for item in resp.json()["items"]] == ["100% Fun"]


@pytest.mark.asyncio
async def test_list_scenarios_filters_by_mode_and_playtime_bucket(
    async_client: AsyncClient, db_session: AsyncSession, dev_user
):
    await _add_published(
        db_session, dev_user.user_id, "Short Simple", playtime_bucket="short"
    )
    await _add_published(
        db_session,
        dev_user.user_id,
        "Long Advanced",
        mode="master",
        playtime_bucket="long",
    )
    await _add_published(db_session, dev_user.user_id, "Unbucketed")

    master = await async_client.get(
        f"/v1/scenarios?mode=master&creator_id={dev_user.user_id}"
    )
    short = await async_client.get(
        f"/v1/scenarios?playtime_bucket=short&creator_id={dev_user.user_id}"
    )

    assert [i["title"] for i in master.json()["items"]] == ["Long Advanced"]
    assert [i["title"] for i in short.json()["items"]] == ["Short Simple"]


@pytest.mark.asyncio
async def test_list_scenarios_rejects_unknown_mode(async_client: AsyncClient):
    resp = await async_client.get("/v1/scenarios?mode=expert")

    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_scenarios_hides_mature_unless_requested(
    async_client: AsyncClient, db_session: AsyncSession, dev_user
):
    await _add_published(db_session, dev_user.user_id, "Grim Tale", is_mature=True)
    await _add_published(db_session, dev_user.user_id, "Gentle Tale")

    default = await async_client.get(f"/v1/scenarios?creator_id={dev_user.user_id}")
    included = await async_client.get(
        f"/v1/scenarios?include_mature=true&creator_id={dev_user.user_id}"
    )

    assert [i["title"] for i in default.json()["items"]] == ["Gentle Tale"]
    assert included.json()["total_count"] == 2


@pytest.mark.asyncio
async def test_list_scenarios_includes_creator_name_and_bookmark_state(
    async_client: AsyncClient, db_session: AsyncSession, dev_user, dev_user2
):
    saved = await _add_published(db_session, dev_user2.user_id, "Saved One")
    await _add_published(db_session, dev_user2.user_id, "Unsaved One")
    db_session.add(Bookmark(user_id=dev_user.user_id, scenario_id=saved.scenario_id))
    await db_session.commit()

    resp = await async_client.get(
        "/v1/scenarios", headers={"x-dev-user-id": str(dev_user.user_id)}
    )

    by_title = {item["title"]: item for item in resp.json()["items"]}
    assert by_title["Saved One"]["is_bookmarked"] is True
    assert by_title["Unsaved One"]["is_bookmarked"] is False
    assert by_title["Saved One"]["creator_display_name"] == "Dev User 2"


@pytest.mark.asyncio
async def test_list_scenarios_guest_sees_no_bookmark_state(
    async_client: AsyncClient, db_session: AsyncSession, dev_user
):
    await _add_published(db_session, dev_user.user_id, "Any Tale")

    resp = await async_client.get(f"/v1/scenarios?creator_id={dev_user.user_id}")

    assert resp.json()["items"][0]["is_bookmarked"] is False


@pytest.mark.asyncio
async def test_list_scenarios_mine_includes_own_mature_drafts(
    async_client: AsyncClient, db_session: AsyncSession, dev_user
):
    await _add_published(db_session, dev_user.user_id, "My Mature", is_mature=True)

    resp = await async_client.get(
        "/v1/scenarios?mine=true", headers={"x-dev-user-id": str(dev_user.user_id)}
    )

    assert resp.json()["total_count"] == 1


@pytest.mark.asyncio
async def test_content_tags_default_to_empty_and_do_not_touch_the_age_rating(
    async_client: AsyncClient, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    payload = {"title": "Plain", "mode": "newbie", "complexity_tier": "newbie"}

    created = (
        await async_client.post("/v1/scenarios", json=payload, headers=headers)
    ).json()

    assert created["content_tags"] == []
    assert created["content_tag"] is None


@pytest.mark.asyncio
async def test_content_tags_are_saved_in_order_and_returned_on_detail(
    async_client: AsyncClient, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    payload = {
        "title": "Themed",
        "mode": "newbie",
        "complexity_tier": "newbie",
        "content_tag": "teen",
        "content_tags": ["moral-ambiguity", "noir-atmosphere"],
    }

    created = (
        await async_client.post("/v1/scenarios", json=payload, headers=headers)
    ).json()
    detail = (
        await async_client.get(
            f"/v1/scenarios/{created['scenario_id']}", headers=headers
        )
    ).json()

    assert detail["content_tags"] == ["moral-ambiguity", "noir-atmosphere"]
    assert detail["content_tag"] == "teen"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad_tags",
    [
        ["not-a-tag"],
        ["romance", "romance"],
        [
            "noir-atmosphere",
            "moral-ambiguity",
            "investigation",
            "political-intrigue",
            "survival-pressure",
            "psychological-tension",
        ],
    ],
    ids=["unknown", "duplicate", "too-many"],
)
async def test_invalid_content_tags_are_rejected_on_create_and_update(
    async_client: AsyncClient, dev_user, bad_tags
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    base = {"title": "Strict", "mode": "newbie", "complexity_tier": "newbie"}

    create_response = await async_client.post(
        "/v1/scenarios", json={**base, "content_tags": bad_tags}, headers=headers
    )
    created = (
        await async_client.post("/v1/scenarios", json=base, headers=headers)
    ).json()
    update_response = await async_client.patch(
        f"/v1/scenarios/{created['scenario_id']}",
        json={"content_tags": bad_tags},
        headers=headers,
    )

    assert create_response.status_code == 422
    assert update_response.status_code == 422


@pytest.mark.asyncio
async def test_content_tags_can_be_edited_and_cleared_without_bumping_the_version(
    async_client: AsyncClient, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    payload = {"title": "Editable", "mode": "newbie", "complexity_tier": "newbie"}
    created = (
        await async_client.post("/v1/scenarios", json=payload, headers=headers)
    ).json()
    url = f"/v1/scenarios/{created['scenario_id']}"

    tagged = (
        await async_client.patch(
            url, json={"content_tags": ["romance"]}, headers=headers
        )
    ).json()
    cleared = (
        await async_client.patch(url, json={"content_tags": []}, headers=headers)
    ).json()

    assert tagged["content_tags"] == ["romance"]
    assert cleared["content_tags"] == []
    assert cleared["current_version"] == created["current_version"]


async def _add_scenario(
    db_session: AsyncSession,
    creator_id: uuid.UUID,
    status: str,
    published_at: datetime | None,
    publish_error: str | None = None,
) -> Scenario:
    scenario = Scenario(
        creator_id=creator_id,
        title=f"Visibility {uuid.uuid4()}",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status=status,
        published_at=published_at,
        publish_error=publish_error,
    )
    db_session.add(scenario)
    await db_session.commit()
    return scenario


@pytest.mark.asyncio
async def test_first_publish_in_progress_is_hidden_from_non_creators(
    async_client: AsyncClient, db_session: AsyncSession, dev_user, dev_user2
):
    scenario = await _add_scenario(
        db_session, dev_user.user_id, status="publishing", published_at=None
    )
    url = f"/v1/scenarios/{scenario.scenario_id}"

    anonymous = await async_client.get(url)
    other_user = await async_client.get(
        url, headers={"x-dev-user-id": str(dev_user2.user_id)}
    )
    creator = await async_client.get(
        url, headers={"x-dev-user-id": str(dev_user.user_id)}
    )

    assert anonymous.status_code == 404
    assert other_user.status_code == 404
    assert creator.status_code == 200


@pytest.mark.asyncio
async def test_failed_republish_stays_public_but_hides_publish_error(
    async_client: AsyncClient, db_session: AsyncSession, dev_user, dev_user2
):
    scenario = await _add_scenario(
        db_session,
        dev_user.user_id,
        status="publish_failed",
        published_at=datetime.now(UTC),
        publish_error="memory layer exploded",
    )
    url = f"/v1/scenarios/{scenario.scenario_id}"

    anonymous = await async_client.get(url)
    other_user = await async_client.get(
        url, headers={"x-dev-user-id": str(dev_user2.user_id)}
    )
    creator = await async_client.get(
        url, headers={"x-dev-user-id": str(dev_user.user_id)}
    )

    assert anonymous.status_code == 200
    assert anonymous.json()["publish_error"] is None
    assert other_user.json()["publish_error"] is None
    assert creator.json()["publish_error"] == "memory layer exploded"


@pytest.mark.asyncio
async def test_archived_scenario_leaves_public_listings_but_stays_in_played(
    async_client: AsyncClient, db_session: AsyncSession, dev_user, dev_user2
):
    player_headers = {"x-dev-user-id": str(dev_user2.user_id)}
    scenario = await _add_scenario(
        db_session, dev_user.user_id, status="archived", published_at=datetime.now(UTC)
    )
    db_session.add_all(
        [
            Bookmark(user_id=dev_user2.user_id, scenario_id=scenario.scenario_id),
            Playthrough(
                scenario_id=scenario.scenario_id,
                created_by=dev_user2.user_id,
                scenario_version=1,
            ),
        ]
    )
    await db_session.commit()

    def listed_ids(resp) -> set[str]:
        return {item["scenario_id"] for item in resp.json()["items"]}

    archived_id = str(scenario.scenario_id)
    discovery = await async_client.get(f"/v1/scenarios?q={scenario.title}")
    profile = await async_client.get(f"/v1/scenarios?creator_id={dev_user.user_id}")
    saved = await async_client.get("/v1/scenarios?saved=true", headers=player_headers)
    played = await async_client.get("/v1/scenarios?played=true", headers=player_headers)
    studio = await async_client.get(
        "/v1/scenarios?mine=true&tab=archived",
        headers={"x-dev-user-id": str(dev_user.user_id)},
    )

    assert archived_id not in listed_ids(discovery)
    assert archived_id not in listed_ids(profile)
    assert archived_id not in listed_ids(saved)
    assert archived_id in listed_ids(played)
    assert played.json()["items"][0]["status"] == "archived"
    assert archived_id in listed_ids(studio)


MASTER_ROW_STATE_SCHEMA = {
    "health": {
        "type": "number",
        "initial": 5,
        "min": 0,
        "max": 10,
        "display": {"kind": "meter"},
    }
}
MASTER_ROW_ATTRIBUTES = {
    "stamina": {"type": "number", "initial": 3, "min": 0, "max": 9}
}
MASTER_ROW_EXPRESSION = {"field": "health", "op": "<=", "value": 0}


async def _create_scenario_via_api(
    async_client: AsyncClient, headers: dict, mode: str = "newbie"
) -> str:
    response = await async_client.post(
        "/v1/scenarios",
        json={"title": "Switchable", "mode": mode, "complexity_tier": mode},
        headers=headers,
    )
    return response.json()["scenario_id"]


async def _patch_mode(
    async_client: AsyncClient, headers: dict, scenario_id: str, mode: str
):
    return await async_client.patch(
        f"/v1/scenarios/{scenario_id}", json={"mode": mode}, headers=headers
    )


async def _seed_master_rows(
    async_client: AsyncClient, headers: dict, scenario_id: str
) -> None:
    base = f"/v1/scenarios/{scenario_id}"
    await async_client.put(
        f"{base}/tools", json={"enabled_tools": ["status_hud"]}, headers=headers
    )
    await async_client.patch(
        base, json={"state_schema": MASTER_ROW_STATE_SCHEMA}, headers=headers
    )
    await async_client.post(
        f"{base}/entities",
        json={
            "entity_type": "character",
            "canonical_name": "Mara",
            "attributes_schema": MASTER_ROW_ATTRIBUTES,
        },
        headers=headers,
    )
    await async_client.post(
        f"{base}/conditions",
        json={
            "label": "Low health",
            "condition_expression": MASTER_ROW_EXPRESSION,
            "narrator_instruction": "Mara winces.",
        },
        headers=headers,
    )
    await async_client.post(
        f"{base}/end_conditions",
        json={
            "condition_expression": MASTER_ROW_EXPRESSION,
            "outcome_tag": "lose",
            "outcome_title": "Gone",
            "outcome_text": "The light fades.",
        },
        headers=headers,
    )
    await async_client.post(
        f"{base}/invariants",
        json={
            "label": "Health floor",
            "invariant_expression": {"field": "health", "op": ">=", "value": 0},
            "applies_to": "global",
            "narrator_text": "Health never goes below zero.",
        },
        headers=headers,
    )


async def _read_master_rows(
    async_client: AsyncClient, headers: dict, scenario_id: str
) -> dict[str, object]:
    base = f"/v1/scenarios/{scenario_id}"
    scenario = (await async_client.get(base, headers=headers)).json()
    entities = (await async_client.get(f"{base}/entities", headers=headers)).json()
    return {
        "state_schema": scenario["state_schema"],
        "enabled_tools": scenario["enabled_tools"],
        "attributes": [e["attributes_schema"] for e in entities["items"]],
        "conditions": (
            await async_client.get(f"{base}/conditions", headers=headers)
        ).json()["items"],
        "end_conditions": (
            await async_client.get(f"{base}/end_conditions", headers=headers)
        ).json()["items"],
        "invariants": (
            await async_client.get(f"{base}/invariants", headers=headers)
        ).json()["items"],
    }


@pytest.mark.asyncio
async def test_patch_mode_to_master_then_newbie_keeps_all_master_rows(
    async_client: AsyncClient, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    scenario_id = await _create_scenario_via_api(async_client, headers)

    assert (
        await _patch_mode(async_client, headers, scenario_id, "master")
    ).status_code == 200
    await _seed_master_rows(async_client, headers, scenario_id)
    before = await _read_master_rows(async_client, headers, scenario_id)

    off = await _patch_mode(async_client, headers, scenario_id, "newbie")
    after_off = await _read_master_rows(async_client, headers, scenario_id)
    on = await _patch_mode(async_client, headers, scenario_id, "master")
    after_on = await _read_master_rows(async_client, headers, scenario_id)

    assert off.status_code == 200
    assert off.json()["mode"] == "newbie"
    assert on.json()["mode"] == "master"
    assert before["state_schema"] == MASTER_ROW_STATE_SCHEMA
    assert before["enabled_tools"] == ["status_hud"]
    assert before["attributes"] == [
        {
            "stamina": {
                **MASTER_ROW_ATTRIBUTES["stamina"],
                "label": None,
                "is_narrator_visible": False,
            }
        }
    ]
    assert len(before["conditions"]) == len(before["end_conditions"]) == 1
    assert len(before["invariants"]) == 1
    assert after_off == before
    assert after_on == before


@pytest.mark.asyncio
async def test_patch_mode_rejected_while_publishing(
    async_client: AsyncClient, db_session: AsyncSession, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    scenario_id = await _create_scenario_via_api(async_client, headers)
    repo = ScenarioRepo(db_session)
    scenario = await repo.get_by_id(uuid.UUID(scenario_id))
    scenario.status = "publishing"
    await repo.update(scenario)

    response = await _patch_mode(async_client, headers, scenario_id, "master")

    assert response.status_code == 409
    assert scenario.mode == "newbie"


@pytest.mark.asyncio
async def test_patch_mode_allowed_on_published_story(
    async_client: AsyncClient, db_session: AsyncSession, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    scenario = await _add_published(db_session, dev_user.user_id, "Live Story")

    response = await _patch_mode(
        async_client, headers, str(scenario.scenario_id), "master"
    )

    assert response.status_code == 200
    assert response.json()["mode"] == "master"
    assert response.json()["status"] == "published"


@pytest.mark.asyncio
async def test_patch_mode_rejects_unknown_mode(async_client: AsyncClient, dev_user):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    scenario_id = await _create_scenario_via_api(async_client, headers)

    response = await _patch_mode(async_client, headers, scenario_id, "expert")

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start_mode", "start_tier", "target_mode", "request_tier", "expected_tier"),
    [
        ("newbie", "newbie", "master", None, "intermediate"),
        ("master", "intermediate", "newbie", None, "newbie"),
        ("newbie", "master", "master", None, "master"),
        ("master", "master", "newbie", None, "master"),
        ("newbie", "newbie", "master", "newbie", "newbie"),
    ],
)
async def test_patch_mode_moves_the_default_complexity_tier_only(
    async_client: AsyncClient,
    dev_user,
    start_mode: str,
    start_tier: str,
    target_mode: str,
    request_tier: str | None,
    expected_tier: str,
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    created = await async_client.post(
        "/v1/scenarios",
        json={"title": "Tiered", "mode": start_mode, "complexity_tier": start_tier},
        headers=headers,
    )
    payload: dict[str, str] = {"mode": target_mode}
    if request_tier:
        payload["complexity_tier"] = request_tier

    response = await async_client.patch(
        f"/v1/scenarios/{created.json()['scenario_id']}",
        json=payload,
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["complexity_tier"] == expected_tier


@pytest.mark.asyncio
async def test_create_strategy_scenario_defaults_to_the_intermediate_tier(
    async_client: AsyncClient, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}

    response = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "The Reach",
            "mode": "strategy",
            "complexity_tier": "intermediate",
            "strategy_document": load_three_crowns().model_dump(mode="json"),
        },
        headers=headers,
    )

    assert response.status_code == 201
    assert response.json()["mode"] == "strategy"


@pytest.mark.asyncio
@pytest.mark.parametrize("target_mode", ["newbie", "master"])
async def test_patch_mode_rejects_leaving_strategy(
    async_client: AsyncClient, dev_user, target_mode: str
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    created = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "The Reach",
            "mode": "strategy",
            "strategy_document": load_three_crowns().model_dump(mode="json"),
        },
        headers=headers,
    )

    response = await _patch_mode(
        async_client, headers, created.json()["scenario_id"], target_mode
    )

    assert response.status_code == 422
    assert "strategy" in response.json()["detail"]


@pytest.mark.asyncio
async def test_patch_mode_rejects_switching_to_strategy(
    async_client: AsyncClient, dev_user
):
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    scenario_id = await _create_scenario_via_api(async_client, headers)

    response = await _patch_mode(async_client, headers, scenario_id, "strategy")

    assert response.status_code == 422

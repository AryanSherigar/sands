"""Integration tests for Scenario Focus endpoints and review turn-count gating."""

import uuid
from datetime import UTC, datetime

import pytest
from app.db.models.playthrough import Playthrough
from app.db.models.review import ScenarioReview
from app.db.models.scenario import Scenario
from app.db.models.scenario_map import ScenarioMap
from app.db.models.scenario_minigame import ScenarioMinigame
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    user_repo = UserRepo(db_session)
    return await user_repo.create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )


@pytest.mark.asyncio
async def test_get_scenario_focus_details(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
) -> None:
    """Test retrieving scenario focus details including creator name and initial states."""
    scenario = Scenario(
        creator_id=dev_user.user_id,
        title="The Sunken Temple",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        logline="Explore the flooded ruins of Eldoria.",
        world_data={"lore": "An ancient temple submerged in water."},
        setup_schema=[{"id": "name", "label": "Character Name", "type": "text"}],
        status="published",
        published_at=datetime.now(UTC),
    )
    db_session.add(scenario)
    await db_session.commit()

    response = await async_client.get(f"/v1/scenarios/{scenario.scenario_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "The Sunken Temple"
    assert data["creator_display_name"] == dev_user.display_name
    assert data["is_bookmarked"] is False
    assert data["can_review"] is False


@pytest.mark.asyncio
async def test_bookmark_toggle_flow(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
) -> None:
    """Test bookmarking and unbookmarking a scenario."""
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    scenario = Scenario(
        creator_id=dev_user.user_id,
        title="Crypt of Whispers",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
    )
    db_session.add(scenario)
    await db_session.commit()

    # Toggle Bookmark ON
    bm_res = await async_client.post(
        f"/v1/scenarios/{scenario.scenario_id}/bookmark",
        headers=headers,
    )
    assert bm_res.status_code == 200
    assert bm_res.json()["is_bookmarked"] is True

    # Check GET scenario response indicates is_bookmarked: True
    get_res = await async_client.get(
        f"/v1/scenarios/{scenario.scenario_id}", headers=headers
    )
    assert get_res.json()["is_bookmarked"] is True

    # Toggle Bookmark OFF
    bm_res_2 = await async_client.post(
        f"/v1/scenarios/{scenario.scenario_id}/bookmark",
        headers=headers,
    )
    assert bm_res_2.status_code == 200
    assert bm_res_2.json()["is_bookmarked"] is False


@pytest.mark.asyncio
async def test_review_submission_gating(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
) -> None:
    """Test that users with <10 turns are blocked and users with >=10 turns can post reviews."""
    headers = {"x-dev-user-id": str(dev_user.user_id)}
    scenario = Scenario(
        creator_id=dev_user.user_id,
        title="Dragon's Peak",
        mode="newbie",
        complexity_tier="intermediate",
        player_count_support="solo",
        status="published",
    )
    db_session.add(scenario)
    await db_session.commit()

    # 1. Attempt to post review without any playthrough -> 403 Forbidden
    fail_res = await async_client.post(
        f"/v1/scenarios/{scenario.scenario_id}/reviews",
        json={"rating": 5, "comment": "Amazing scenario!"},
        headers=headers,
    )
    assert fail_res.status_code == 403

    # 2. Create playthrough with 5 turns -> still fails
    pt_short = Playthrough(
        scenario_id=scenario.scenario_id,
        created_by=dev_user.user_id,
        turn_count=5,
        status="active",
        scenario_version=1,
    )
    db_session.add(pt_short)
    await db_session.commit()

    fail_res_2 = await async_client.post(
        f"/v1/scenarios/{scenario.scenario_id}/reviews",
        json={"rating": 5, "comment": "Short run!"},
        headers=headers,
    )
    assert fail_res_2.status_code == 403

    # 3. Create playthrough with 12 turns -> succeeds
    pt_long = Playthrough(
        scenario_id=scenario.scenario_id,
        created_by=dev_user.user_id,
        turn_count=12,
        status="completed",
        scenario_version=1,
    )
    db_session.add(pt_long)
    await db_session.commit()

    success_res = await async_client.post(
        f"/v1/scenarios/{scenario.scenario_id}/reviews",
        json={"rating": 5, "comment": "Masterpiece adventure!"},
        headers=headers,
    )
    assert success_res.status_code == 201
    rev_data = success_res.json()
    assert rev_data["rating"] == 5
    assert rev_data["comment"] == "Masterpiece adventure!"

    # 4. GET reviews list
    list_res = await async_client.get(f"/v1/scenarios/{scenario.scenario_id}/reviews")
    assert list_res.status_code == 200
    reviews_list = list_res.json()
    assert reviews_list["total_count"] == 1
    assert reviews_list["items"][0]["comment"] == "Masterpiece adventure!"


def _published_scenario(creator_id: uuid.UUID, title: str, **overrides) -> Scenario:
    return Scenario(
        creator_id=creator_id,
        title=title,
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
        published_at=datetime.now(UTC),
        **overrides,
    )


@pytest.mark.asyncio
async def test_scenario_detail_includes_creator_block(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
) -> None:
    """Detail exposes avatar, bio and the count of the creator's OTHER published scenarios."""
    other_creator = await UserRepo(db_session).create(
        auth_provider_id=f"other-auth-{uuid.uuid4()}", display_name="Someone Else"
    )
    dev_user.bio = "Architecting noir."
    dev_user.avatar_url = "https://example.com/avatar.png"
    focus = _published_scenario(dev_user.user_id, "Focus")
    db_session.add_all(
        [
            focus,
            _published_scenario(dev_user.user_id, "Sibling One"),
            _published_scenario(dev_user.user_id, "Sibling Two"),
            Scenario(
                creator_id=dev_user.user_id,
                title="Unfinished",
                mode="newbie",
                complexity_tier="newbie",
                player_count_support="solo",
                status="draft",
            ),
            _published_scenario(other_creator.user_id, "Not Theirs"),
        ]
    )
    await db_session.commit()

    response = await async_client.get(f"/v1/scenarios/{focus.scenario_id}")

    data = response.json()
    assert data["creator_avatar_url"] == "https://example.com/avatar.png"
    assert data["creator_bio"] == "Architecting noir."
    assert data["creator_other_scenarios_count"] == 2


@pytest.mark.asyncio
async def test_scenario_detail_creator_block_defaults_when_creator_has_nothing(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
) -> None:
    focus = _published_scenario(dev_user.user_id, "Solo Work")
    db_session.add(focus)
    await db_session.commit()

    data = (await async_client.get(f"/v1/scenarios/{focus.scenario_id}")).json()

    assert data["creator_avatar_url"] is None
    assert data["creator_bio"] is None
    assert data["creator_other_scenarios_count"] == 0


@pytest.mark.asyncio
async def test_scenario_detail_reports_maps_and_minigames(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
) -> None:
    plain = _published_scenario(dev_user.user_id, "Plain")
    rich = _published_scenario(dev_user.user_id, "Rich")
    db_session.add_all([plain, rich])
    await db_session.flush()
    db_session.add_all(
        [
            ScenarioMap(scenario_id=rich.scenario_id, name="Harbor"),
            ScenarioMinigame(
                scenario_id=rich.scenario_id,
                label="Dodge",
                minigame_type="dodge",
                priority=1,
                outcome_mode="binary",
                dodge_config={"difficulty": 2},
            ),
        ]
    )
    await db_session.commit()

    plain_data = (await async_client.get(f"/v1/scenarios/{plain.scenario_id}")).json()
    rich_data = (await async_client.get(f"/v1/scenarios/{rich.scenario_id}")).json()

    assert (plain_data["has_maps"], plain_data["has_minigames"]) == (False, False)
    assert (rich_data["has_maps"], rich_data["has_minigames"]) == (True, True)


@pytest.mark.asyncio
async def test_reviews_return_rating_counts_over_all_reviews_not_just_the_page(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
) -> None:
    scenario = _published_scenario(dev_user.user_id, "Reviewed")
    db_session.add(scenario)
    await db_session.flush()
    user_repo = UserRepo(db_session)
    for rating in (5, 5, 2):
        reviewer = await user_repo.create(
            auth_provider_id=f"reviewer-{uuid.uuid4()}", display_name="Reviewer"
        )
        db_session.add(
            ScenarioReview(
                scenario_id=scenario.scenario_id,
                user_id=reviewer.user_id,
                rating=rating,
            )
        )
    await db_session.commit()

    response = await async_client.get(
        f"/v1/scenarios/{scenario.scenario_id}/reviews", params={"limit": 1}
    )

    data = response.json()
    assert len(data["items"]) == 1
    assert data["total_count"] == 3
    assert data["rating_counts"] == [
        {"stars": 5, "count": 2},
        {"stars": 4, "count": 0},
        {"stars": 3, "count": 0},
        {"stars": 2, "count": 1},
        {"stars": 1, "count": 0},
    ]


@pytest.mark.asyncio
async def test_reviews_pages_do_not_overlap(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
) -> None:
    scenario = _published_scenario(dev_user.user_id, "Paged")
    db_session.add(scenario)
    await db_session.flush()
    user_repo = UserRepo(db_session)
    for _ in range(3):
        reviewer = await user_repo.create(
            auth_provider_id=f"pager-{uuid.uuid4()}", display_name="Pager"
        )
        db_session.add(
            ScenarioReview(
                scenario_id=scenario.scenario_id, user_id=reviewer.user_id, rating=4
            )
        )
    await db_session.commit()
    url = f"/v1/scenarios/{scenario.scenario_id}/reviews"

    first = (await async_client.get(url, params={"limit": 2, "offset": 0})).json()
    second = (await async_client.get(url, params={"limit": 2, "offset": 2})).json()

    first_ids = {item["review_id"] for item in first["items"]}
    second_ids = {item["review_id"] for item in second["items"]}
    assert len(first_ids) == 2
    assert len(second_ids) == 1
    assert first_ids.isdisjoint(second_ids)


@pytest.mark.asyncio
async def test_reviews_return_viewers_own_review_even_off_the_loaded_page(
    async_client: AsyncClient,
    db_session: AsyncSession,
    dev_user,
) -> None:
    scenario = _published_scenario(dev_user.user_id, "Mine Somewhere")
    db_session.add(scenario)
    await db_session.flush()
    user_repo = UserRepo(db_session)
    viewer = await user_repo.create(
        auth_provider_id=f"viewer-{uuid.uuid4()}", display_name="Viewer"
    )
    db_session.add(
        ScenarioReview(
            scenario_id=scenario.scenario_id,
            user_id=viewer.user_id,
            rating=3,
            comment="Fine.",
        )
    )
    await db_session.flush()
    for _ in range(2):
        other = await user_repo.create(
            auth_provider_id=f"later-{uuid.uuid4()}", display_name="Later"
        )
        db_session.add(
            ScenarioReview(
                scenario_id=scenario.scenario_id, user_id=other.user_id, rating=5
            )
        )
    await db_session.commit()
    url = f"/v1/scenarios/{scenario.scenario_id}/reviews"

    signed_in = await async_client.get(
        url,
        params={"limit": 1},
        headers={"x-dev-user-id": str(viewer.user_id)},
    )
    guest = await async_client.get(url, params={"limit": 1})

    own = signed_in.json()["own_review"]
    assert own["user_id"] == str(viewer.user_id)
    assert (own["rating"], own["comment"]) == (3, "Fine.")
    assert guest.json()["own_review"] is None

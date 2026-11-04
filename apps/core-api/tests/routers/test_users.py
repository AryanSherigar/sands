"""Integration tests for User Profile REST endpoints."""

import uuid

import pytest
from app.db.models.playthrough import Playthrough
from app.db.models.review import ScenarioReview
from app.db.models.scenario import Scenario
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def test_user(db_session: AsyncSession):
    user = await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}",
        display_name="Eldrin the Mage",
    )
    user.bio = "A traveler from the high peaks."
    user.avatar_url = "/avatars/mage.webp"
    user.banner_url = "/banners/library.webp"
    await db_session.flush()
    return user


@pytest.fixture
async def published_scenario(db_session: AsyncSession, test_user):
    scenario = Scenario(
        creator_id=test_user.user_id,
        title="Tower of Arcana",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
        play_count=42,
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


@pytest.fixture
async def test_playthrough(db_session: AsyncSession, test_user, published_scenario):
    playthrough = Playthrough(
        scenario_id=published_scenario.scenario_id,
        created_by=test_user.user_id,
        turn_count=15,
        status="active",
        scenario_version=1,
        state={
            "setup": {
                "character_name": "Valerius",
                "archetype": "Arcane Scholar",
            }
        },
        scenario_snapshot={"title": "Tower of Arcana"},
    )
    db_session.add(playthrough)
    await db_session.flush()
    return playthrough


@pytest.fixture
async def test_review(db_session: AsyncSession, test_user, published_scenario):
    review = ScenarioReview(
        scenario_id=published_scenario.scenario_id,
        user_id=test_user.user_id,
        rating=5,
        comment="An epic adventure through mysterious spires!",
    )
    db_session.add(review)
    await db_session.flush()
    return review


@pytest.mark.asyncio
async def test_get_my_profile_authenticated(
    async_client: AsyncClient, test_user, published_scenario, test_playthrough
):
    headers = {"x-dev-user-id": str(test_user.user_id)}
    response = await async_client.get("/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user.user_id)
    assert data["display_name"] == "Eldrin the Mage"
    assert data["bio"] == "A traveler from the high peaks."
    assert data["avatar_url"] == "/avatars/mage.webp"
    assert data["banner_url"] == "/banners/library.webp"
    assert "auth_provider_id" in data
    assert data["stats"]["scenarios_authored_count"] == 1
    assert data["stats"]["total_plays_received"] == 42
    assert data["stats"]["campaigns_played_count"] == 1
    assert data["stats"]["victories_count"] == 0
    assert data["stats"]["total_turns_taken"] == 15


@pytest.mark.asyncio
async def test_get_my_profile_unauthenticated(async_client: AsyncClient):
    response = await async_client.get("/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_my_profile(async_client: AsyncClient, test_user):
    headers = {"x-dev-user-id": str(test_user.user_id)}
    payload = {
        "display_name": "Archmage Eldrin",
        "bio": "Keeper of the forbidden scrolls.",
        "avatar_url": "/avatars/custom.png",
        "banner_url": "/banners/custom.png",
    }
    response = await async_client.patch("/v1/users/me", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Archmage Eldrin"
    assert data["bio"] == "Keeper of the forbidden scrolls."
    assert data["avatar_url"] == "/avatars/custom.png"
    assert data["banner_url"] == "/banners/custom.png"


@pytest.mark.asyncio
async def test_patch_my_profile_voice_output_enabled(
    async_client: AsyncClient, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}

    enable_response = await async_client.patch(
        "/v1/users/me", json={"voice_output_enabled": True}, headers=headers
    )
    assert enable_response.status_code == 200
    assert enable_response.json()["voice_output_enabled"] is True

    disable_response = await async_client.patch(
        "/v1/users/me", json={"voice_output_enabled": False}, headers=headers
    )
    assert disable_response.status_code == 200
    assert disable_response.json()["voice_output_enabled"] is False


@pytest.mark.asyncio
async def test_get_public_profile(
    async_client: AsyncClient, test_user, published_scenario
):
    response = await async_client.get(f"/v1/users/{test_user.user_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(test_user.user_id)
    assert data["display_name"] == "Eldrin the Mage"
    assert data["stats"]["scenarios_authored_count"] == 1
    assert "auth_provider_id" not in data


@pytest.mark.asyncio
async def test_get_public_profile_not_found(async_client: AsyncClient):
    random_id = uuid.uuid4()
    response = await async_client.get(f"/v1/users/{random_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_list_my_playthroughs(
    async_client: AsyncClient, test_user, test_playthrough
):
    headers = {"x-dev-user-id": str(test_user.user_id)}
    response = await async_client.get("/v1/users/me/playthroughs", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    campaign = data[0]
    assert campaign["playthrough_id"] == str(test_playthrough.playthrough_id)
    assert campaign["scenario_title"] == "Tower of Arcana"
    assert campaign["character_name"] == "Valerius"
    assert campaign["character_archetype"] == "Arcane Scholar"
    assert campaign["turn_count"] == 15


@pytest.mark.asyncio
async def test_list_user_reviews(
    async_client: AsyncClient, test_user, test_review, published_scenario
):
    response = await async_client.get(f"/v1/users/{test_user.user_id}/reviews")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["scenario_title"] == "Tower of Arcana"
    assert data[0]["rating"] == 5
    assert "epic adventure" in data[0]["review_text"]


@pytest.mark.asyncio
async def test_abandon_playthrough(
    async_client: AsyncClient, test_user, test_playthrough, db_session: AsyncSession
):
    headers = {"x-dev-user-id": str(test_user.user_id)}
    from app.db.models.participant import Participant

    participant = Participant(
        playthrough_id=test_playthrough.playthrough_id,
        user_id=test_user.user_id,
        role="owner",
        turn_order_position=1,
    )
    db_session.add(participant)
    await db_session.flush()

    response = await async_client.post(
        f"/v1/playthroughs/{test_playthrough.playthrough_id}/abandon",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "abandoned"


@pytest.mark.asyncio
async def test_complete_onboarding_saves_answers(
    async_client: AsyncClient, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}
    payload = {
        "display_name": "Onboarded Eldrin",
        "bio": "Fresh off the road.",
        "preferred_genres": ["Horror", "Mystery"],
    }
    response = await async_client.post(
        "/v1/users/me/onboarding", json=payload, headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Onboarded Eldrin"
    assert data["bio"] == "Fresh off the road."
    assert data["preferred_genres"] == ["Horror", "Mystery"]
    assert data["onboarding_completed_at"] is not None


@pytest.mark.asyncio
async def test_complete_onboarding_without_answers_still_completes(
    async_client: AsyncClient, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}
    response = await async_client.post(
        "/v1/users/me/onboarding", json={}, headers=headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["display_name"] == "Eldrin the Mage"
    assert data["preferred_genres"] == []
    assert data["onboarding_completed_at"] is not None


@pytest.mark.asyncio
async def test_complete_onboarding_is_idempotent(
    async_client: AsyncClient, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}
    first = await async_client.post(
        "/v1/users/me/onboarding",
        json={"preferred_genres": ["Horror"]},
        headers=headers,
    )
    second = await async_client.post(
        "/v1/users/me/onboarding",
        json={"display_name": "Overwrite", "preferred_genres": ["Sci-Fi"]},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["display_name"] == "Eldrin the Mage"
    assert second.json()["preferred_genres"] == ["Horror"]
    assert (
        second.json()["onboarding_completed_at"]
        == first.json()["onboarding_completed_at"]
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"preferred_genres": ["a", "b", "c", "d"]},
        {"display_name": ""},
        {"preferred_genres": [""]},
    ],
)
async def test_complete_onboarding_rejects_invalid_payload(
    async_client: AsyncClient, test_user, payload: dict[str, object]
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}
    response = await async_client.post(
        "/v1/users/me/onboarding", json=payload, headers=headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_complete_onboarding_unauthenticated(async_client: AsyncClient) -> None:
    response = await async_client.post("/v1/users/me/onboarding", json={})
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_show_mature_defaults_to_false_and_can_be_toggled(
    async_client: AsyncClient, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}

    initial = (await async_client.get("/v1/users/me", headers=headers)).json()
    enabled = await async_client.patch(
        "/v1/users/me", json={"show_mature": True}, headers=headers
    )
    persisted = (await async_client.get("/v1/users/me", headers=headers)).json()
    disabled = await async_client.patch(
        "/v1/users/me", json={"show_mature": False}, headers=headers
    )

    assert initial["show_mature"] is False
    assert enabled.json()["show_mature"] is True
    assert persisted["show_mature"] is True
    assert disabled.json()["show_mature"] is False


@pytest.mark.asyncio
async def test_updating_other_fields_leaves_show_mature_untouched(
    async_client: AsyncClient, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}
    await async_client.patch(
        "/v1/users/me", json={"show_mature": True}, headers=headers
    )

    response = await async_client.patch(
        "/v1/users/me", json={"bio": "New bio"}, headers=headers
    )

    assert response.json()["bio"] == "New bio"
    assert response.json()["show_mature"] is True


@pytest.mark.asyncio
async def test_show_mature_rejects_non_boolean_values(
    async_client: AsyncClient, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}

    response = await async_client.patch(
        "/v1/users/me", json={"show_mature": "maybe"}, headers=headers
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_updates_preferred_genres_after_onboarding(
    async_client: AsyncClient, test_user
) -> None:
    headers = {"x-dev-user-id": str(test_user.user_id)}
    await async_client.post(
        "/v1/users/me/onboarding",
        json={"preferred_genres": ["Noir"]},
        headers=headers,
    )

    response = await async_client.patch(
        "/v1/users/me",
        json={"preferred_genres": ["Horror", "Mystery"]},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["preferred_genres"] == ["Horror", "Mystery"]

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.config import settings
from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.middleware.internal_auth import HEADER_INTERNAL_SERVICE_TOKEN
from app.repositories.creator_stats_repo import CreatorStatsRepo
from app.repositories.profile_overview_repo import ProfileOverviewRepo
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

TEST_TOKEN = "test-internal-token-secret"


@pytest.fixture
def internal_headers(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    monkeypatch.setattr(settings, "internal_service_token", TEST_TOKEN)
    return {HEADER_INTERNAL_SERVICE_TOKEN: TEST_TOKEN}


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )


@pytest.fixture
async def test_scenario(db_session: AsyncSession, dev_user) -> Scenario:
    scenario = Scenario(
        scenario_id=uuid.uuid4(),
        creator_id=dev_user.user_id,
        title="Test Scenario",
        status="published",
        visibility="public",
        mode="strategy",
        complexity_tier="master",
        player_count_support="solo",
        play_count=0,
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


@pytest.fixture
async def test_playthrough(
    db_session: AsyncSession, test_scenario: Scenario, dev_user: User
) -> Playthrough:
    playthrough = Playthrough(
        playthrough_id=uuid.uuid4(),
        scenario_id=test_scenario.scenario_id,
        created_by=dev_user.user_id,
        turn_count=0,
        status="active",
        scenario_version=1,
    )
    db_session.add(playthrough)
    await db_session.flush()

    participant = Participant(
        participant_id=uuid.uuid4(),
        playthrough_id=playthrough.playthrough_id,
        user_id=dev_user.user_id,
        role="owner",
        turn_order_position=1,
    )
    db_session.add(participant)
    await db_session.flush()
    return playthrough


async def test_internal_sync_requires_token(
    async_client: AsyncClient, test_playthrough: Playthrough
) -> None:
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"
    response = await async_client.patch(url, json={"turn_count": 1})
    assert response.status_code in (401, 503)


async def test_internal_sync_rejects_invalid_token(
    async_client: AsyncClient,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
) -> None:
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"
    bad_headers = {HEADER_INTERNAL_SERVICE_TOKEN: "wrong-token"}
    response = await async_client.patch(
        url, json={"turn_count": 1}, headers=bad_headers
    )
    assert response.status_code == 401


async def test_internal_sync_updates_turn_count_monotonically(
    async_client: AsyncClient,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
) -> None:
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"

    first_res = await async_client.patch(
        url, json={"turn_count": 3}, headers=internal_headers
    )
    assert first_res.status_code == 200
    assert first_res.json()["turn_count"] == 3
    assert first_res.json()["status"] == "active"

    # Out of order smaller turn should not roll back
    second_res = await async_client.patch(
        url, json={"turn_count": 2}, headers=internal_headers
    )
    assert second_res.status_code == 200
    assert second_res.json()["turn_count"] == 3


async def test_internal_sync_increments_scenario_play_count_at_threshold(
    async_client: AsyncClient,
    test_scenario: Scenario,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"
    assert test_scenario.play_count == 0

    # Advance to turn 9 (below threshold 10)
    res9 = await async_client.patch(
        url, json={"turn_count": 9}, headers=internal_headers
    )
    assert res9.status_code == 200
    await db_session.refresh(test_scenario)
    assert test_scenario.play_count == 0

    # Advance to turn 10 (crosses threshold)
    res10 = await async_client.patch(
        url, json={"turn_count": 10}, headers=internal_headers
    )
    assert res10.status_code == 200
    await db_session.refresh(test_scenario)
    assert test_scenario.play_count == 1

    # Advance to turn 11 (already crossed)
    res11 = await async_client.patch(
        url, json={"turn_count": 11}, headers=internal_headers
    )
    assert res11.status_code == 200
    await db_session.refresh(test_scenario)
    assert test_scenario.play_count == 1


async def test_internal_sync_marks_ended_status(
    async_client: AsyncClient,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
) -> None:
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"
    response = await async_client.patch(
        url, json={"turn_count": 5, "is_ended": True}, headers=internal_headers
    )
    assert response.status_code == 200
    assert response.json()["turn_count"] == 5
    assert response.json()["status"] == "completed"


async def test_internal_sync_records_the_ending_outcome(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
) -> None:
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"
    payload = {
        "turn_count": 9,
        "is_ended": True,
        "ended_outcome_tag": "win",
        "ended_outcome_title": "Victory Conquest",
    }
    response = await async_client.patch(url, json=payload, headers=internal_headers)

    assert response.status_code == 200
    await db_session.refresh(test_playthrough)
    assert test_playthrough.ended_outcome_tag == "win"
    assert test_playthrough.ended_outcome_title == "Victory Conquest"


async def test_internal_sync_returns_404_for_unknown_playthrough(
    async_client: AsyncClient, internal_headers: dict[str, str]
) -> None:
    url = f"/internal/v1/playthroughs/{uuid.uuid4()}/turn"
    response = await async_client.patch(
        url, json={"turn_count": 1}, headers=internal_headers
    )
    assert response.status_code == 404


async def test_internal_sync_updates_get_playthrough_endpoint(
    async_client: AsyncClient,
    test_playthrough: Playthrough,
    dev_user: User,
    internal_headers: dict[str, str],
) -> None:
    user_headers = {"x-dev-user-id": str(dev_user.user_id)}
    playthrough_url = f"/v1/playthroughs/{test_playthrough.playthrough_id}"

    # Before sync, GET returns turn_count 0
    before = await async_client.get(playthrough_url, headers=user_headers)
    assert before.status_code == 200
    assert before.json()["turn_count"] == 0

    # Sync to turn 7
    sync_url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"
    sync_res = await async_client.patch(
        sync_url, json={"turn_count": 7}, headers=internal_headers
    )
    assert sync_res.status_code == 200

    # After sync, player GET immediately sees turn 7
    after = await async_client.get(playthrough_url, headers=user_headers)
    assert after.status_code == 200
    assert after.json()["turn_count"] == 7


async def test_internal_sync_updates_creator_stats_frequencies_and_totals(
    async_client: AsyncClient,
    test_scenario: Scenario,
    dev_user: User,
    internal_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    now = datetime.now(UTC)
    start = now - timedelta(days=7)
    repo = CreatorStatsRepo(db_session)

    # Initially 0 playthroughs
    init_freq = await repo.get_turn_count_frequencies(
        test_scenario.scenario_id, start, now
    )
    assert init_freq == []

    # Create two playthroughs
    pt1 = Playthrough(
        playthrough_id=uuid.uuid4(),
        scenario_id=test_scenario.scenario_id,
        created_by=dev_user.user_id,
        turn_count=0,
        status="active",
        scenario_version=1,
    )
    pt2 = Playthrough(
        playthrough_id=uuid.uuid4(),
        scenario_id=test_scenario.scenario_id,
        created_by=dev_user.user_id,
        turn_count=0,
        status="active",
        scenario_version=1,
    )
    db_session.add_all([pt1, pt2])
    await db_session.flush()

    # Sync pt1 -> turn 4, pt2 -> turn 12
    await async_client.patch(
        f"/internal/v1/playthroughs/{pt1.playthrough_id}/turn",
        json={"turn_count": 4},
        headers=internal_headers,
    )
    await async_client.patch(
        f"/internal/v1/playthroughs/{pt2.playthrough_id}/turn",
        json={"turn_count": 12},
        headers=internal_headers,
    )

    frequencies = await repo.get_turn_count_frequencies(
        test_scenario.scenario_id, start, now
    )
    assert dict(frequencies) == {4: 1, 12: 1}

    totals = await repo.get_playthrough_totals(
        [test_scenario.scenario_id], start, now, [3, 10]
    )
    assert len(totals) == 1
    assert totals[0].plays == 2
    assert totals[0].reached_turn_counts == (2, 1)


async def test_internal_sync_updates_profile_overview_stats(
    async_client: AsyncClient,
    test_scenario: Scenario,
    dev_user: User,
    internal_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    repo = ProfileOverviewRepo(db_session)

    # Initial profile stats
    init_counts = await repo.get_lifetime_counts(dev_user.user_id)
    assert init_counts.turns_taken == 0

    # Create and sync a playthrough
    pt = Playthrough(
        playthrough_id=uuid.uuid4(),
        scenario_id=test_scenario.scenario_id,
        created_by=dev_user.user_id,
        turn_count=0,
        status="active",
        scenario_version=1,
    )
    db_session.add(pt)
    await db_session.flush()

    # Sync turn 8 and completed
    await async_client.patch(
        f"/internal/v1/playthroughs/{pt.playthrough_id}/turn",
        json={"turn_count": 8, "is_ended": True},
        headers=internal_headers,
    )

    # Verify profile stats updated
    after_counts = await repo.get_lifetime_counts(dev_user.user_id)
    assert after_counts.turns_taken == 8
    assert after_counts.stories_completed == 1


async def test_internal_sync_validates_turn_count_non_negative(
    async_client: AsyncClient,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
) -> None:
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"
    response = await async_client.patch(
        url, json={"turn_count": -5}, headers=internal_headers
    )
    assert response.status_code == 422


async def test_internal_sync_preserves_abandoned_status(
    async_client: AsyncClient,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    test_playthrough.status = "abandoned"
    await db_session.flush()

    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"
    response = await async_client.patch(
        url, json={"turn_count": 4, "is_ended": True}, headers=internal_headers
    )
    assert response.status_code == 200
    assert response.json()["status"] == "abandoned"


async def test_internal_sync_direct_threshold_jump(
    async_client: AsyncClient,
    test_scenario: Scenario,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"
    assert test_scenario.play_count == 0

    # Jump straight from turn 0 to turn 15
    response = await async_client.patch(
        url, json={"turn_count": 15}, headers=internal_headers
    )
    assert response.status_code == 200
    await db_session.refresh(test_scenario)
    assert test_scenario.play_count == 1


async def test_internal_sync_idempotency_on_repeated_syncs(
    async_client: AsyncClient,
    test_scenario: Scenario,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
    db_session: AsyncSession,
) -> None:
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/turn"

    for _ in range(3):
        res = await async_client.patch(
            url, json={"turn_count": 10}, headers=internal_headers
        )
        assert res.status_code == 200
        assert res.json()["turn_count"] == 10

    await db_session.refresh(test_scenario)
    # play_count must only increment once, not 3 times!
    assert test_scenario.play_count == 1


async def _end_run(
    async_client: AsyncClient, playthrough: Playthrough, headers: dict[str, str]
) -> None:
    url = f"/internal/v1/playthroughs/{playthrough.playthrough_id}/turn"
    await async_client.patch(
        url, json={"turn_count": 9, "is_ended": True}, headers=headers
    )


async def test_outcome_text_is_stored_once_a_run_has_ended(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
) -> None:
    await _end_run(async_client, test_playthrough, internal_headers)
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/outcome-text"

    response = await async_client.patch(
        url, json={"ended_outcome_text": "The crown endured."}, headers=internal_headers
    )

    assert response.status_code == 200
    await db_session.refresh(test_playthrough)
    assert test_playthrough.ended_outcome_text == "The crown endured."


async def test_outcome_text_is_never_overwritten(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
) -> None:
    await _end_run(async_client, test_playthrough, internal_headers)
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/outcome-text"
    await async_client.patch(
        url, json={"ended_outcome_text": "First."}, headers=internal_headers
    )

    await async_client.patch(
        url, json={"ended_outcome_text": "Second."}, headers=internal_headers
    )

    await db_session.refresh(test_playthrough)
    assert test_playthrough.ended_outcome_text == "First."


async def test_outcome_text_is_ignored_while_the_run_is_still_active(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
) -> None:
    url = f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/outcome-text"

    response = await async_client.patch(
        url, json={"ended_outcome_text": "Too early."}, headers=internal_headers
    )

    assert response.status_code == 200
    await db_session.refresh(test_playthrough)
    assert test_playthrough.ended_outcome_text is None


async def test_outcome_text_needs_the_service_token_and_a_known_run(
    async_client: AsyncClient,
    test_playthrough: Playthrough,
    internal_headers: dict[str, str],
) -> None:
    unauthenticated = await async_client.patch(
        f"/internal/v1/playthroughs/{test_playthrough.playthrough_id}/outcome-text",
        json={"ended_outcome_text": "x"},
    )
    unknown = await async_client.patch(
        f"/internal/v1/playthroughs/{uuid.uuid4()}/outcome-text",
        json={"ended_outcome_text": "x"},
        headers=internal_headers,
    )

    assert unauthenticated.status_code in (401, 403)
    assert unknown.status_code == 404

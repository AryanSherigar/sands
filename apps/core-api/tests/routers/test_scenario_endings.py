"""Integration tests for GET /v1/scenarios/{id}/endings."""

import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from app.db.models.end_condition import EndCondition
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import add_playthrough, make_scenario, make_user

EARLY = datetime(2026, 10, 26, tzinfo=UTC)


async def _add_condition(
    session: AsyncSession,
    scenario: Scenario,
    title: str,
    text: str,
    tag: str = "win",
    is_secret: bool = False,
    priority: int = 0,
) -> EndCondition:
    condition = EndCondition(
        scenario_id=scenario.scenario_id,
        outcome_tag=tag,
        outcome_title=title,
        outcome_text=text,
        is_secret=is_secret,
        priority=priority,
    )
    session.add(condition)
    await session.flush()
    return condition


async def _finish_run(
    session: AsyncSession,
    scenario: Scenario,
    player: User,
    condition: EndCondition,
    turn_count: int,
    ended_at: datetime = EARLY,
    is_playtest: bool = False,
) -> Playthrough:
    run = await add_playthrough(
        session,
        scenario,
        player,
        turn_count=turn_count,
        status="completed",
        outcome_tag=condition.outcome_tag,
        outcome_title=condition.outcome_title,
        outcome_id=condition.end_condition_id,
        is_playtest=is_playtest,
    )
    run.ended_outcome_text = condition.outcome_text
    run.updated_at = ended_at
    await session.flush()
    return run


def _as_viewer(user: User) -> dict[str, str]:
    return {"x-dev-user-id": str(user.user_id)}


@pytest.fixture
async def story(db_session: AsyncSession):
    creator = await make_user(db_session, "Creator")
    scenario = await make_scenario(db_session, creator, mode="master")
    ashen = await _add_condition(
        db_session, scenario, "Ashen Dawn", "You burned the ledger.", priority=1
    )
    consumed = await _add_condition(
        db_session, scenario, "Consumed", "The harbor took you.", "lose", priority=2
    )
    vigil = await _add_condition(
        db_session,
        scenario,
        "The Hidden Vigil",
        "You waited in the dark.",
        is_secret=True,
        priority=3,
    )
    await db_session.commit()
    return scenario, creator, ashen, consumed, vigil


@pytest.mark.asyncio
async def test_signed_out_gets_only_a_count_that_excludes_unfound_secrets(
    async_client: AsyncClient, story
) -> None:
    scenario, *_ = story

    response = await async_client.get(f"/v1/scenarios/{scenario.scenario_id}/endings")

    assert response.status_code == 200
    body = response.json()
    assert body == {"total_count": 2, "found": None}
    text = json.dumps(body)
    assert "Ashen" not in text
    assert "Vigil" not in text


@pytest.mark.asyncio
async def test_signed_in_player_with_no_finished_runs_sees_zero_found(
    async_client: AsyncClient, db_session: AsyncSession, story
) -> None:
    scenario, *_ = story
    player = await make_user(db_session, "Player")
    await db_session.commit()

    body = (
        await async_client.get(
            f"/v1/scenarios/{scenario.scenario_id}/endings", headers=_as_viewer(player)
        )
    ).json()

    assert body == {"total_count": 2, "found": []}


@pytest.mark.asyncio
async def test_found_ending_carries_name_text_turn_and_date_and_nothing_else_leaks(
    async_client: AsyncClient, db_session: AsyncSession, story
) -> None:
    scenario, _creator, ashen, *_ = story
    player = await make_user(db_session, "Player")
    await _finish_run(db_session, scenario, player, ashen, turn_count=24)
    await db_session.commit()

    response = await async_client.get(
        f"/v1/scenarios/{scenario.scenario_id}/endings", headers=_as_viewer(player)
    )

    body = response.json()
    assert body["total_count"] == 2
    assert len(body["found"]) == 1
    found = body["found"][0]
    assert found["title"] == "Ashen Dawn"
    assert found["text"] == "You burned the ledger."
    assert found["outcome_tag"] == "win"
    assert found["turn_reached"] == 24
    assert found["ending_id"] == str(ashen.end_condition_id)
    assert found["found_at"].startswith(EARLY.date().isoformat())
    text = json.dumps(body)
    assert "Consumed" not in text
    assert "harbor took you" not in text
    assert "Vigil" not in text


@pytest.mark.asyncio
async def test_a_found_secret_ending_is_revealed_and_counted(
    async_client: AsyncClient, db_session: AsyncSession, story
) -> None:
    scenario, _creator, _ashen, _consumed, vigil = story
    player = await make_user(db_session, "Player")
    await _finish_run(db_session, scenario, player, vigil, turn_count=40)
    await db_session.commit()

    body = (
        await async_client.get(
            f"/v1/scenarios/{scenario.scenario_id}/endings", headers=_as_viewer(player)
        )
    ).json()

    assert body["total_count"] == 3
    assert [ending["title"] for ending in body["found"]] == ["The Hidden Vigil"]


@pytest.mark.asyncio
async def test_reaching_the_same_ending_twice_lists_it_once_using_the_earliest_run(
    async_client: AsyncClient, db_session: AsyncSession, story
) -> None:
    scenario, _creator, ashen, *_ = story
    player = await make_user(db_session, "Player")
    await _finish_run(
        db_session, scenario, player, ashen, 30, ended_at=EARLY + timedelta(days=5)
    )
    await _finish_run(db_session, scenario, player, ashen, 18, ended_at=EARLY)
    await db_session.commit()

    body = (
        await async_client.get(
            f"/v1/scenarios/{scenario.scenario_id}/endings", headers=_as_viewer(player)
        )
    ).json()

    assert len(body["found"]) == 1
    assert body["found"][0]["turn_reached"] == 18


@pytest.mark.asyncio
async def test_other_players_and_playtest_runs_do_not_count_as_found(
    async_client: AsyncClient, db_session: AsyncSession, story
) -> None:
    scenario, _creator, ashen, consumed, _vigil = story
    me = await make_user(db_session, "Me")
    someone_else = await make_user(db_session, "Someone Else")
    await _finish_run(db_session, scenario, someone_else, ashen, 20)
    await _finish_run(db_session, scenario, me, consumed, 9, is_playtest=True)
    await db_session.commit()

    body = (
        await async_client.get(
            f"/v1/scenarios/{scenario.scenario_id}/endings", headers=_as_viewer(me)
        )
    ).json()

    assert body["found"] == []


@pytest.mark.asyncio
async def test_a_story_without_author_endings_reports_zero(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    creator = await make_user(db_session, "Creator")
    scenario = await make_scenario(db_session, creator, mode="newbie")
    await db_session.commit()

    body = (
        await async_client.get(f"/v1/scenarios/{scenario.scenario_id}/endings")
    ).json()

    assert body["total_count"] == 0


@pytest.mark.asyncio
async def test_drafts_are_visible_only_to_their_creator(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    creator = await make_user(db_session, "Creator")
    stranger = await make_user(db_session, "Stranger")
    draft = await make_scenario(db_session, creator, mode="master", status="draft")
    await db_session.commit()
    url = f"/v1/scenarios/{draft.scenario_id}/endings"

    assert (await async_client.get(url)).status_code == 404
    assert (
        await async_client.get(url, headers=_as_viewer(stranger))
    ).status_code == 404
    assert (await async_client.get(url, headers=_as_viewer(creator))).status_code == 200


@pytest.mark.asyncio
async def test_missing_and_archived_scenarios_are_404(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    creator = await make_user(db_session, "Creator")
    archived = await make_scenario(db_session, creator, status="archived")
    await db_session.commit()

    assert (
        await async_client.get(f"/v1/scenarios/{uuid.uuid4()}/endings")
    ).status_code == 404
    assert (
        await async_client.get(f"/v1/scenarios/{archived.scenario_id}/endings")
    ).status_code == 404

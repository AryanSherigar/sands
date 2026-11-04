import uuid
from datetime import UTC, datetime

import pytest
from app.db.models.scenario import Scenario
from app.repositories.user_repo import UserRepo
from scripts.publish_scenario import (
    EXIT_FAILED,
    EXIT_OK,
    OUTCOME_ALREADY_PUBLISHED,
    OUTCOME_MISSING,
    OUTCOME_PUBLISHING,
    OUTCOME_STARTED,
    PublishResult,
    build_parser,
    start_publish,
)
from sqlalchemy.ext.asyncio import AsyncSession


async def make_scenario(
    db_session: AsyncSession, status: str, published_at: datetime | None = None
) -> Scenario:
    creator = await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )
    scenario = Scenario(
        creator_id=creator.user_id,
        title="Publish Tale",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status=status,
        published_at=published_at,
        narrator_persona="A narrator.",
        world_data={"lore": "Lore."},
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


@pytest.mark.asyncio
async def test_a_missing_scenario_is_reported(db_session) -> None:
    result = await start_publish(db_session, uuid.uuid4())

    assert result.outcome == OUTCOME_MISSING
    assert not result.is_ok


@pytest.mark.asyncio
async def test_a_live_scenario_is_left_untouched(db_session) -> None:
    scenario = await make_scenario(db_session, "published", datetime.now(UTC))

    result = await start_publish(db_session, scenario.scenario_id)

    assert result.outcome == OUTCOME_ALREADY_PUBLISHED
    assert result.is_ok
    assert scenario.status == "published"


@pytest.mark.asyncio
async def test_a_draft_is_flipped_to_publishing(db_session) -> None:
    scenario = await make_scenario(db_session, "draft")

    result = await start_publish(db_session, scenario.scenario_id)

    assert result.outcome == OUTCOME_STARTED
    assert scenario.status == "publishing"


@pytest.mark.asyncio
async def test_a_scenario_already_publishing_is_reported_not_raised(db_session) -> None:
    scenario = await make_scenario(db_session, "publishing")

    result = await start_publish(db_session, scenario.scenario_id)

    assert result.outcome == OUTCOME_PUBLISHING
    assert not result.is_ok


def test_exit_codes_distinguish_success_from_failure() -> None:
    assert EXIT_OK == 0
    assert EXIT_FAILED == 1
    assert PublishResult(uuid.uuid4(), "published").is_ok
    assert not PublishResult(uuid.uuid4(), "failed", "boom").is_ok


def test_the_parser_accepts_several_scenario_ids() -> None:
    first, second = str(uuid.uuid4()), str(uuid.uuid4())

    args = build_parser().parse_args(["--scenario-id", first, "--scenario-id", second])

    assert [str(item) for item in args.scenario_id] == [first, second]

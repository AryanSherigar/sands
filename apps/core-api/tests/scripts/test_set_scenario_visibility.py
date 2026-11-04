import uuid
from datetime import UTC, datetime

import pytest
from app.db.models.scenario import Scenario
from app.repositories.scenario_access_repo import ScenarioAccessRepo
from scripts.set_scenario_visibility import (
    EXIT_FAILED,
    EXIT_OK,
    build_parser,
    run_command,
)
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import make_user


async def run(session: AsyncSession, *argv: str):
    return await run_command(build_parser().parse_args(argv), session)


async def make_scenario(db_session: AsyncSession, creator) -> Scenario:
    scenario = Scenario(
        creator_id=creator.user_id,
        title="Appraisal Tale",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
        status="published",
        published_at=datetime.now(UTC),
        narrator_persona="A narrator.",
        world_data={"lore": "Lore."},
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


async def test_making_a_scenario_private_reports_creator_only(db_session):
    scenario = await make_scenario(db_session, await make_user(db_session))

    result = await run(
        db_session,
        "--scenario-id",
        str(scenario.scenario_id),
        "--visibility",
        "private",
    )

    assert result.exit_code == EXIT_OK
    assert scenario.visibility == "private"
    assert "creator only" in result.output
    assert "Appraisal Tale" in result.output


async def test_the_command_is_idempotent(db_session):
    scenario = await make_scenario(db_session, await make_user(db_session))
    args = ("--scenario-id", str(scenario.scenario_id), "--visibility", "private")
    await run(db_session, *args)

    result = await run(db_session, *args)

    assert result.exit_code == EXIT_OK
    assert scenario.visibility == "private"


async def test_a_scenario_can_be_made_public_again(db_session):
    scenario = await make_scenario(db_session, await make_user(db_session))
    await run(
        db_session,
        "--scenario-id",
        str(scenario.scenario_id),
        "--visibility",
        "private",
    )

    await run(
        db_session, "--scenario-id", str(scenario.scenario_id), "--visibility", "public"
    )

    assert scenario.visibility == "public"


async def test_allowing_and_revoking_a_user(db_session):
    scenario = await make_scenario(db_session, await make_user(db_session))
    guest = await make_user(db_session, display_name="Guest")
    base = ("--scenario-id", str(scenario.scenario_id))

    allowed = await run(db_session, *base, "--allow", str(guest.user_id))
    assert str(guest.user_id) in allowed.output
    repo = ScenarioAccessRepo(db_session)
    assert await repo.is_allowed(scenario.scenario_id, guest.user_id) is True

    revoked = await run(db_session, *base, "--revoke", str(guest.user_id))
    assert revoked.exit_code == EXIT_OK
    assert await repo.is_allowed(scenario.scenario_id, guest.user_id) is False


async def test_allowing_an_unknown_user_fails_without_a_trace(db_session):
    scenario = await make_scenario(db_session, await make_user(db_session))

    result = await run(
        db_session,
        "--scenario-id",
        str(scenario.scenario_id),
        "--allow",
        str(uuid.uuid4()),
    )

    assert result.exit_code == EXIT_FAILED
    assert "Failed" in result.output


async def test_an_unknown_scenario_fails(db_session):
    result = await run(
        db_session, "--scenario-id", str(uuid.uuid4()), "--visibility", "private"
    )

    assert result.exit_code == EXIT_FAILED


def test_an_unknown_visibility_is_rejected_by_the_parser():
    with pytest.raises(SystemExit):
        build_parser().parse_args(
            ["--scenario-id", str(uuid.uuid4()), "--visibility", "secret"]
        )

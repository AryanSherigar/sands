"""Integration tests for TurnLogRepo.get_latest_narrations."""

from datetime import UTC, datetime

import pytest
from app.repositories.turn_log_repo import TurnLogRepo
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import (
    add_playthrough,
    add_turn_log,
    make_scenario,
    make_user,
)

STAMP = datetime(2026, 10, 26, 12, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_latest_narrations_picks_highest_turn_per_playthrough(
    db_session: AsyncSession,
) -> None:
    player = await make_user(db_session)
    scenario = await make_scenario(db_session, player)
    first = await add_playthrough(db_session, scenario, player, turn_count=2)
    second = await add_playthrough(db_session, scenario, player, turn_count=1)
    await add_turn_log(db_session, first, 1, STAMP, "old first")
    await add_turn_log(db_session, first, 2, STAMP, "new first")
    await add_turn_log(db_session, second, 1, STAMP, None)

    result = await TurnLogRepo(db_session).get_latest_narrations(
        [first.playthrough_id, second.playthrough_id]
    )

    assert result == {first.playthrough_id: "new first", second.playthrough_id: None}


@pytest.mark.asyncio
async def test_latest_narrations_empty_input_and_missing_turns(
    db_session: AsyncSession,
) -> None:
    player = await make_user(db_session)
    scenario = await make_scenario(db_session, player)
    no_turns = await add_playthrough(db_session, scenario, player)
    repo = TurnLogRepo(db_session)
    assert await repo.get_latest_narrations([]) == {}
    assert await repo.get_latest_narrations([no_turns.playthrough_id]) == {}

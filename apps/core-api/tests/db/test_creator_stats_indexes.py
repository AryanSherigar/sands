"""The indexes backing creator stats exist in the test schema."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

EXPECTED_INDEXES = {
    "idx_playthroughs_scenario_created_at",
    "idx_scenario_reviews_scenario_created_at",
    "idx_bookmarks_scenario_id",
    "idx_playthrough_shares_playthrough_id",
}


@pytest.mark.asyncio
async def test_creator_stats_indexes_exist(db_session: AsyncSession) -> None:
    result = await db_session.execute(
        text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
    )
    assert set(result.scalars().all()) >= EXPECTED_INDEXES

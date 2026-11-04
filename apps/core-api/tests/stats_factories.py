"""Shared DB builders for creator stats tests."""

import uuid
from datetime import UTC, datetime, timedelta

from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

STATS_NOW = datetime.now(UTC)
RECENT = STATS_NOW - timedelta(days=1)
WINDOW_START = STATS_NOW - timedelta(days=30)
THRESHOLDS = [3, 10]


async def make_user(session: AsyncSession, display_name: str = "Player") -> User:
    user = User(
        user_id=uuid.uuid4(),
        display_name=display_name,
        auth_provider_id=f"test-auth-{uuid.uuid4()}",
    )
    session.add(user)
    await session.flush()
    return user


async def make_scenario(
    session: AsyncSession,
    creator: User,
    mode: str = "master",
    status: str = "published",
    genre_tags: list[str] | None = None,
) -> Scenario:
    scenario = Scenario(
        scenario_id=uuid.uuid4(),
        creator_id=creator.user_id,
        title=f"Stats scenario {uuid.uuid4().hex[:6]}",
        mode=mode,
        complexity_tier=mode,
        player_count_support="both",
        status=status,
        genre_tags=genre_tags or [],
    )
    session.add(scenario)
    await session.flush()
    return scenario


async def add_playthrough(
    session: AsyncSession,
    scenario: Scenario,
    player: User,
    turn_count: int = 0,
    status: str = "active",
    outcome_tag: str | None = None,
    outcome_title: str | None = None,
    is_playtest: bool = False,
    created_at: datetime = RECENT,
    scenario_version: int = 1,
    state: dict[str, object] | None = None,
    outcome_id: uuid.UUID | None = None,
    snapshot: dict[str, object] | None = None,
) -> Playthrough:
    playthrough = Playthrough(
        scenario_id=scenario.scenario_id,
        created_by=player.user_id,
        turn_count=turn_count,
        status=status,
        ended_outcome_tag=outcome_tag,
        ended_outcome_title=outcome_title,
        ended_outcome_id=outcome_id,
        is_playtest=is_playtest,
        created_at=created_at,
        scenario_version=scenario_version,
        state=state or {},
        scenario_snapshot=snapshot or {},
    )
    session.add(playthrough)
    await session.flush()
    return playthrough


async def add_turn_log(
    session: AsyncSession,
    playthrough: Playthrough,
    turn_number: int,
    created_at: datetime,
    narration_text: str | None = None,
) -> TurnLog:
    turn = TurnLog(
        playthrough_id=playthrough.playthrough_id,
        turn_number=turn_number,
        action_text="act",
        narration_text=narration_text,
        created_at=created_at,
    )
    session.add(turn)
    await session.flush()
    return turn

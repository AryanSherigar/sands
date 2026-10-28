"""Queries behind the profile Endings tab."""

import uuid
from dataclasses import dataclass
from datetime import datetime

from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

END_CONDITIONS_KEY = "end_conditions"


@dataclass(frozen=True)
class EndedRunRow:
    scenario_id: uuid.UUID
    outcome_id: uuid.UUID | None
    outcome_title: str
    outcome_tag: str | None


@dataclass(frozen=True)
class EndedRunDetailRow(EndedRunRow):
    outcome_text: str | None = None
    turn_count: int = 0
    ended_at: datetime | None = None


@dataclass(frozen=True)
class SnapshotEndingsRow:
    scenario_id: uuid.UUID
    scenario_title: str
    last_played_at: datetime
    end_conditions: list[dict[str, object]]


class EndingsRepo:
    """Repository for a user's finished runs and each story's latest snapshot."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_ended_runs(self, user_id: uuid.UUID) -> list[EndedRunRow]:
        stmt = select(
            Playthrough.scenario_id,
            Playthrough.ended_outcome_id,
            Playthrough.ended_outcome_title,
            Playthrough.ended_outcome_tag,
        ).where(
            Playthrough.created_by == user_id,
            Playthrough.is_playtest.is_(False),
            Playthrough.ended_outcome_title.is_not(None),
        )
        result = await self.session.execute(stmt)
        return [EndedRunRow(*row) for row in result.all()]

    async def list_ended_run_details(
        self, user_id: uuid.UUID, scenario_id: uuid.UUID
    ) -> list[EndedRunDetailRow]:
        """A player's finished non-playtest runs of one scenario, earliest ending first."""
        stmt = (
            select(
                Playthrough.scenario_id,
                Playthrough.ended_outcome_id,
                Playthrough.ended_outcome_title,
                Playthrough.ended_outcome_tag,
                Playthrough.ended_outcome_text,
                Playthrough.turn_count,
                Playthrough.updated_at,
            )
            .where(
                Playthrough.created_by == user_id,
                Playthrough.scenario_id == scenario_id,
                Playthrough.is_playtest.is_(False),
                Playthrough.ended_outcome_title.is_not(None),
            )
            .order_by(Playthrough.updated_at.asc(), Playthrough.playthrough_id.asc())
        )
        result = await self.session.execute(stmt)
        return [EndedRunDetailRow(*row) for row in result.all()]

    async def list_latest_snapshot_endings(
        self, user_id: uuid.UUID
    ) -> list[SnapshotEndingsRow]:
        # TRADE-OFF: selects only the end_conditions JSON path, not the whole
        # scenario_snapshot, because snapshots carry entities, facts and maps.
        conditions = Playthrough.scenario_snapshot[END_CONDITIONS_KEY].as_json()
        latest = (
            select(
                Playthrough.scenario_id,
                Scenario.title,
                Playthrough.created_at,
                conditions,
            )
            .join(Scenario, Playthrough.scenario_id == Scenario.scenario_id)
            .where(
                Playthrough.created_by == user_id,
                Playthrough.is_playtest.is_(False),
                Playthrough.turn_count >= 1,
            )
            .distinct(Playthrough.scenario_id)
            .order_by(Playthrough.scenario_id, Playthrough.created_at.desc())
        )
        result = await self.session.execute(latest)
        rows = [
            SnapshotEndingsRow(scenario_id, title, created_at, list(raw or []))
            for scenario_id, title, created_at, raw in result.all()
        ]
        return sorted(rows, key=lambda row: row.last_played_at, reverse=True)

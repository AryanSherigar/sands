"""TurnMetrics persistence."""

import uuid

from app.db.models.turn_metrics import TurnMetrics
from app.models.turn_metrics import TurnMetricsRecord
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession


class TurnMetricsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        turn_id: uuid.UUID,
        playthrough_id: uuid.UUID,
        turn_number: int,
        record: TurnMetricsRecord,
    ) -> TurnMetrics:
        values = record.model_dump(mode="json")
        metrics = TurnMetrics(
            turn_id=turn_id,
            playthrough_id=playthrough_id,
            turn_number=turn_number,
            **values,
        )
        self.session.add(metrics)
        await self.session.flush()
        return metrics

    async def increment_replay_count(self, turn_id: uuid.UUID) -> None:
        await self.session.execute(
            update(TurnMetrics)
            .where(TurnMetrics.turn_id == turn_id)
            .values(replay_count=TurnMetrics.replay_count + 1)
        )

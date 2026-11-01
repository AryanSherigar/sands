"""TurnLog data repository for direct database operations."""

import uuid

from app.db.models.turn_log import TurnLog
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement


class TurnLogRepo:
    """Repository managing direct SQLAlchemy queries for TurnLog entity."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        playthrough_id: uuid.UUID,
        turn_number: int,
        participant_id: uuid.UUID | None,
        action_text: str,
        narration_text: str | None,
        action_mode: str = "do",
        tool_calls: list[dict[str, object]] | None = None,
        image_url: str | None = None,
        location_id: str | None = None,
        scene_image_prompt: str | None = None,
        audio_url: str | None = None,
        accepted_delta: dict[str, object] | None = None,
        client_action_id: uuid.UUID | None = None,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        model_name: str | None = None,
        turn_id: uuid.UUID | None = None,
    ) -> TurnLog:
        """Persist a new append-only TurnLog entity."""
        turn_log = TurnLog(
            **({"turn_id": turn_id} if turn_id else {}),
            playthrough_id=playthrough_id,
            turn_number=turn_number,
            participant_id=participant_id,
            action_text=action_text,
            action_mode=action_mode,
            narration_text=narration_text,
            tool_calls=tool_calls or [],
            image_url=image_url,
            location_id=location_id,
            scene_image_prompt=scene_image_prompt,
            audio_url=audio_url,
            accepted_delta=accepted_delta or {},
            client_action_id=client_action_id,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            model_name=model_name,
        )
        self.session.add(turn_log)
        await self.session.flush()
        return turn_log

    async def get_by_client_action_id(
        self, playthrough_id: uuid.UUID, client_action_id: uuid.UUID
    ) -> TurnLog | None:
        """Fetch the turn a client-generated action id already produced, if any."""
        result = await self.session.execute(
            select(TurnLog).where(
                TurnLog.playthrough_id == playthrough_id,
                TurnLog.client_action_id == client_action_id,
            )
        )
        return result.scalars().first()

    async def list_recent(self, playthrough_id: uuid.UUID, limit: int) -> list[TurnLog]:
        """Fetch the newest `limit` turns, returned oldest first."""
        result = await self.session.execute(
            select(TurnLog)
            .where(TurnLog.playthrough_id == playthrough_id, ~_is_combat_event())
            .order_by(TurnLog.turn_number.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def count_combat_events(
        self, playthrough_id: uuid.UUID, through_turn: int | None = None
    ) -> int:
        """Count durable combat receipts without changing their event sequence."""
        query = (
            select(func.count())
            .select_from(TurnLog)
            .where(TurnLog.playthrough_id == playthrough_id, _is_combat_event())
        )
        if through_turn is not None:
            query = query.where(TurnLog.turn_number <= through_turn)
        result = await self.session.execute(query)
        return result.scalar_one()

    async def list_by_turn_ids(self, turn_ids: list[uuid.UUID]) -> list[TurnLog]:
        """Fetch turn logs by primary key in one query."""
        if not turn_ids:
            return []
        result = await self.session.execute(
            select(TurnLog).where(TurnLog.turn_id.in_(turn_ids))
        )
        return list(result.scalars().all())

    async def find_latest_by_location(
        self, playthrough_id: uuid.UUID, location_id: str
    ) -> TurnLog | None:
        """Find the most recent turn log with a scene image for this location,
        used to keep repeated 'see' actions at the same place visually
        consistent (see docs/plans image-generation grounding notes)."""
        query = (
            select(TurnLog)
            .where(
                TurnLog.playthrough_id == playthrough_id,
                TurnLog.location_id == location_id,
                TurnLog.image_url.is_not(None),
            )
            .order_by(TurnLog.turn_number.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()


def _is_combat_event() -> ColumnElement[bool]:
    return or_(
        *(
            TurnLog.tool_calls.contains([{"tool_name": name}])
            for name in ("_combat_start", "_combat_action", "_combat_outcome")
        )
    )

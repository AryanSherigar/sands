"""TurnMetrics ORM model (mirrored in the turn-resolution-service).

One operational row per persisted alpha turn, written by TRS in the turn commit.
See docs/specs/closed-alpha/alpha-data-collection.spec.md.
"""

import uuid

from sqlalchemy import ForeignKey, Integer, text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Text

from app.db.base import Base, CreatedAtMixin


class TurnMetrics(Base, CreatedAtMixin):
    """Latency, memory health, engine and check facts for one turn."""

    __tablename__ = "turn_metrics"

    turn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("turn_logs.turn_id", ondelete="CASCADE"),
        primary_key=True,
    )
    playthrough_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("playthroughs.playthrough_id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)
    first_token_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    generation_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    step_durations: Mapped[dict[str, int]] = mapped_column(
        JSONB, nullable=False, default=dict
    )
    memory_degraded_reasons: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        server_default=text("'{}'::text[]"),
        default=list,
        nullable=False,
    )
    memory_retrieval_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memory_facts_returned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fired_condition_ids: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        server_default=text("'{}'::text[]"),
        default=list,
        nullable=False,
    )
    dropped_mutation_count: Mapped[int] = mapped_column(
        Integer, server_default="0", default=0, nullable=False
    )
    dropped_mutation_paths: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        server_default=text("'{}'::text[]"),
        default=list,
        nullable=False,
    )
    check_outcomes: Mapped[list[dict[str, object]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb"), default=list, nullable=False
    )
    stat_snapshot: Mapped[dict[str, float]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), default=dict, nullable=False
    )
    replay_count: Mapped[int] = mapped_column(
        Integer, server_default="0", default=0, nullable=False
    )

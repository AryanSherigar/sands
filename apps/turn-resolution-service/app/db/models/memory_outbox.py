"""MemoryOutbox ORM model (mirrors core-api's schema).

Rows are inserted in the same transaction as the product change they describe
and delivered to the memory service by services/memory_relay_service.py.
playthrough_id carries no FK on purpose: delivery must not depend on the
playthrough row still existing, and the purge path removes rows explicitly.
"""

import uuid
from datetime import datetime

from app.db.base import Base, CreatedAtMixin
from sqlalchemy import (
    TIMESTAMP,
    BigInteger,
    CheckConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

ITEM_KIND_REGISTER = "register_playthrough"
ITEM_KIND_TURN = "turn"
ITEM_KIND_FLUSH = "flush"
ITEM_KIND_PARTICIPANTS = "participants"


class MemoryOutbox(Base, CreatedAtMixin):
    """One item bound for the memory service, undelivered until delivered_at is set."""

    __tablename__ = "memory_outbox"

    __table_args__ = (
        CheckConstraint(
            "item_kind IN ('register_playthrough', 'turn', 'participants', 'flush')",
            name="item_kind",
        ),
        UniqueConstraint(
            "playthrough_id",
            "item_kind",
            "sequence",
            name="uq_memory_outbox_playthrough_kind_sequence",
        ),
        Index(
            "ix_memory_outbox_undelivered",
            "playthrough_id",
            "sequence",
            postgresql_where=text("delivered_at IS NULL"),
        ),
    )

    outbox_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    playthrough_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    item_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    sequence: Mapped[int] = mapped_column(nullable=False)
    turn_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    attempt_count: Mapped[int] = mapped_column(
        server_default="0", default=0, nullable=False
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

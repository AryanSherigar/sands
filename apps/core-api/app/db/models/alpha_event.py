"""AlphaEvent ORM model (mirrored in the turn-resolution-service).

Props are validated against a closed registry before they reach this table;
see app/models/alpha_event_props.py.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EVENT_SOURCE_CLIENT = "client"
EVENT_SOURCE_SERVER = "server"


class AlphaEvent(Base):
    """One pseudonymous product or server event from an alpha tester."""

    __tablename__ = "alpha_events"
    __table_args__ = (
        CheckConstraint("source IN ('client', 'server')", name="source"),
        Index("ix_alpha_events_user_id_received_at", "user_id", "received_at"),
        Index("ix_alpha_events_name_received_at", "name", "received_at"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    playthrough_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("playthroughs.playthrough_id", ondelete="CASCADE"),
        nullable=True,
    )
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    props: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), default=dict, nullable=False
    )
    source: Mapped[str] = mapped_column(Text, nullable=False)
    client_ts: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    received_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

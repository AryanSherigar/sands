"""Rate-limit counter and SSE stream-lease ORM models.

Counters back both sliding-window burst limits and UTC-day quotas: one row
per (key, fixed window). See docs/specs/rate-limiting.spec.md.
"""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, Index, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RateLimitCounter(Base):
    __tablename__ = "rate_limit_counters"
    __table_args__ = (Index("ix_rate_limit_counters_expires_at", "expires_at"),)

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    window_start: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), primary_key=True
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )


class RateLimitStreamLease(Base):
    __tablename__ = "rate_limit_stream_leases"
    __table_args__ = (
        Index(
            "ix_rate_limit_stream_leases_subject_expires", "subject_key", "expires_at"
        ),
    )

    lease_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    subject_key: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )

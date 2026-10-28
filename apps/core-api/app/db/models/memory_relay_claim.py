"""Durable ownership and immutable payload for one relay batch per playthrough."""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, BigInteger
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MemoryRelayClaim(Base):
    __tablename__ = "memory_relay_claims"

    playthrough_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True
    )
    delivery_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    ownership_token: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    lease_expires_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False
    )
    outbox_ids: Mapped[list[int]] = mapped_column(ARRAY(BigInteger), nullable=False)
    payload: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)

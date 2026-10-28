"""Alpha invite and redemption ORM models.

Only the SHA-256 hash of an invite code is stored; the plaintext link is
printed once by scripts/alpha_invites.py. See docs/specs/closed-alpha/
alpha-perimeter.spec.md.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin


class AlphaInvite(Base, CreatedAtMixin):
    """A bearer invite link with a limited number of seats."""

    __tablename__ = "alpha_invites"
    __table_args__ = (
        CheckConstraint("max_seats >= 1", name="max_seats_positive"),
        CheckConstraint("seats_used <= max_seats", name="seats_within_max"),
        UniqueConstraint("code_hash", name="uq_alpha_invites_code_hash"),
    )

    invite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    code_hash: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    max_seats: Mapped[int] = mapped_column(Integer, nullable=False)
    seats_used: Mapped[int] = mapped_column(
        Integer, server_default="0", default=0, nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )


class AlphaInviteRedemption(Base):
    """Records which invite admitted a user; one invite per user."""

    __tablename__ = "alpha_invite_redemptions"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_alpha_invite_redemptions_user_id"),
    )

    redemption_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    invite_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("alpha_invites.invite_id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    redeemed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

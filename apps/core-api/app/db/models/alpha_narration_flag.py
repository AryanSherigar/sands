"""AlphaNarrationFlag ORM model: a tester's one-tap "this narration is wrong"."""

import uuid

from sqlalchemy import ForeignKey, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin

FLAG_REASONS = (
    "broke_rule",
    "contradicted",
    "out_of_character",
    "too_long",
    "other",
)
FLAG_NOTE_MAX_CHARS = 500


class AlphaNarrationFlag(Base, CreatedAtMixin):
    """One flag per user per turn; a repeat flag replaces the earlier one."""

    __tablename__ = "alpha_narration_flags"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "turn_id", name="uq_alpha_narration_flags_user_turn"
        ),
    )

    flag_id: Mapped[uuid.UUID] = mapped_column(
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
    playthrough_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("playthroughs.playthrough_id", ondelete="CASCADE"),
        nullable=False,
    )
    turn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("turn_logs.turn_id", ondelete="CASCADE"),
        nullable=False,
    )
    reasons: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default=text("'{}'::text[]"), default=list, nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

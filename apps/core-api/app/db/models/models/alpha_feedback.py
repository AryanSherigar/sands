"""AlphaFeedback ORM model: free-text notes a tester leaves during a run."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin

FEEDBACK_CATEGORIES = ("bug", "confusing", "scary", "other")
FEEDBACK_BODY_MAX_CHARS = 2000


class AlphaFeedback(Base, CreatedAtMixin):
    """One categorised free-text note, optionally tied to a turn number."""

    __tablename__ = "alpha_feedback"
    __table_args__ = (
        CheckConstraint(
            "category IN ('bug', 'confusing', 'scary', 'other')", name="category"
        ),
        CheckConstraint(
            f"char_length(body) <= {FEEDBACK_BODY_MAX_CHARS}", name="body_length"
        ),
    )

    feedback_id: Mapped[uuid.UUID] = mapped_column(
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
    turn_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)

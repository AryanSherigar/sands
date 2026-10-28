"""UserAchievement ORM model: one row per badge a user has earned."""

import uuid
from datetime import datetime

from sqlalchemy import TIMESTAMP, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ACHIEVEMENT_KEY_MAX_LENGTH = 64


class UserAchievement(Base):
    """A persisted award; earned_at is set once and never rewritten."""

    __tablename__ = "user_achievements"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        primary_key=True,
    )
    achievement_key: Mapped[str] = mapped_column(
        String(ACHIEVEMENT_KEY_MAX_LENGTH), primary_key=True
    )
    earned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=text("CURRENT_TIMESTAMP"),
        nullable=False,
    )

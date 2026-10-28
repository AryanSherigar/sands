"""Bookmark ORM model."""

import uuid

from sqlalchemy import ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin


class Bookmark(Base, CreatedAtMixin):
    """User scenario bookmark entity."""

    __tablename__ = "bookmarks"
    __table_args__ = (
        UniqueConstraint("user_id", "scenario_id", name="uq_bookmarks_user_scenario"),
        Index("idx_bookmarks_scenario_id", "scenario_id"),
    )

    bookmark_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        nullable=False,
    )

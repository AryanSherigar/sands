"""MapGenerationJob ORM model.

Persisted rather than held in a process-local dict so a poll served by a
different core-api instance than the one running the job still sees it.
"""

import uuid

from app.db.base import Base, TimestampMixin
from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

MAP_JOB_STATUSES = ("pending", "running", "succeeded", "failed")


class MapGenerationJob(Base, TimestampMixin):
    """One strategy map generation attempt: region image, then painted art."""

    __tablename__ = "map_generation_jobs"

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','running','succeeded','failed')",
            name="ck_map_generation_jobs_status",
        ),
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        nullable=False,
    )
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.user_id", ondelete="RESTRICT"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="pending", default="pending"
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    region_image_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    picture_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_art: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false"), default=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

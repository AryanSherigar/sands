"""AlphaSurveyResponse ORM model: intake and post-run surveys."""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin

SURVEY_KIND_INTAKE = "intake"
SURVEY_KIND_POST_RUN = "post_run"


class AlphaSurveyResponse(Base, CreatedAtMixin):
    """One answered survey; intake is once per user, post-run once per playthrough."""

    __tablename__ = "alpha_survey_responses"
    __table_args__ = (
        CheckConstraint("kind IN ('intake', 'post_run')", name="kind"),
        Index(
            "uq_alpha_survey_responses_intake",
            "user_id",
            unique=True,
            postgresql_where=text("kind = 'intake'"),
        ),
        Index(
            "uq_alpha_survey_responses_post_run",
            "user_id",
            "playthrough_id",
            unique=True,
            postgresql_where=text("kind = 'post_run'"),
        ),
    )

    response_id: Mapped[uuid.UUID] = mapped_column(
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
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    answers: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)

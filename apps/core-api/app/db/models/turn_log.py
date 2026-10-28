"""TurnLog ORM model."""

import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, CreatedAtMixin


class TurnLog(Base, CreatedAtMixin):
    """Append-only turn execution record entity."""

    __tablename__ = "turn_logs"

    __table_args__ = (
        UniqueConstraint(
            "playthrough_id", "turn_number", name="uq_turn_logs_playthrough_turn"
        ),
        UniqueConstraint(
            "playthrough_id",
            "client_action_id",
            name="uq_turn_logs_playthrough_client_action",
        ),
    )

    turn_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    playthrough_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("playthroughs.playthrough_id", ondelete="RESTRICT"),
        nullable=False,
    )
    turn_number: Mapped[int] = mapped_column(nullable=False)
    participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("participants.participant_id", ondelete="RESTRICT"),
        nullable=True,
    )
    action_text: Mapped[str] = mapped_column(Text, nullable=False)
    action_mode: Mapped[str] = mapped_column(
        String(16), server_default=text("'do'"), nullable=False
    )
    narration_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    tool_calls: Mapped[list[object]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        default=list,
        nullable=False,
    )
    accepted_delta: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        server_default=text("'{}'::jsonb"),
        default=dict,
        nullable=False,
    )
    client_action_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    image_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    location_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scene_image_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(64), nullable=True)

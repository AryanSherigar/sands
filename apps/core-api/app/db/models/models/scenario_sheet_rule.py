"""ScenarioSheetRule ORM model (tool `rule_sheet`)."""

import uuid

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy import text as sql_text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ScenarioSheetRule(Base, TimestampMixin):
    """One rule on the player's clipboard. Its live status is engine-owned state
    (`rule_status.<key>`), never stored here (docs/specs/rules-horror-engine/
    rules-and-clipboard-tool.spec.md)."""

    __tablename__ = "scenario_sheet_rules"

    __table_args__ = (
        UniqueConstraint("scenario_id", "key", name="uq_scenario_sheet_rules_key"),
        Index("idx_scenario_sheet_rules_scenario_id", "scenario_id"),
    )

    rule_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sql_text("gen_random_uuid()"),
        default=uuid.uuid4,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("scenarios.scenario_id", ondelete="CASCADE"),
        nullable=False,
    )
    key: Mapped[str] = mapped_column(String(31), nullable=False)
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    corrupted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    initial_status: Mapped[str] = mapped_column(
        String(12), server_default="intact", default="intact", nullable=False
    )
    source_style: Mapped[str] = mapped_column(
        String(10), server_default="typed", default="typed", nullable=False
    )
    is_ai_flaggable: Mapped[bool] = mapped_column(
        Boolean, server_default=sql_text("false"), default=False, nullable=False
    )
    display_order: Mapped[int] = mapped_column(
        Integer, server_default="0", default=0, nullable=False
    )

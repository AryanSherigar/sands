"""ScenarioRuleCheck ORM model (tool `rule_checks`)."""

import uuid

from sqlalchemy import ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class ScenarioRuleCheck(Base, TimestampMixin):
    """A creator-authored timed prompt that opens from state and writes the
    player's answer back into `result_path` (docs/specs/rules-horror-engine/
    rule-checks-tool.spec.md). The kind/params pairing is enforced in Pydantic,
    not as a DB CHECK, matching scenario_minigames."""

    __tablename__ = "scenario_rule_checks"

    __table_args__ = (Index("idx_scenario_rule_checks_scenario_id", "scenario_id"),)

    check_id: Mapped[uuid.UUID] = mapped_column(
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
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_condition_expression: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), default=dict, nullable=False
    )
    priority: Mapped[int] = mapped_column(
        Integer, server_default="0", default=0, nullable=False
    )
    result_path: Mapped[str] = mapped_column(String(255), nullable=False)
    params: Mapped[dict[str, object]] = mapped_column(
        JSONB, server_default=text("'{}'::jsonb"), default=dict, nullable=False
    )
    narrator_instruction_template: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )

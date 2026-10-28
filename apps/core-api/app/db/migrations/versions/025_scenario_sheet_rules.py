"""scenario_sheet_rules table

Revision ID: 025_scenario_sheet_rules
Revises: 024_scenario_rule_checks

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "025_scenario_sheet_rules"
down_revision: str | None = "024_scenario_rule_checks"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenario_sheet_rules",
        sa.Column(
            "rule_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=31), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("corrupted_text", sa.Text(), nullable=True),
        sa.Column(
            "initial_status",
            sa.String(length=12),
            server_default="intact",
            nullable=False,
        ),
        sa.Column(
            "source_style",
            sa.String(length=10),
            server_default="typed",
            nullable=False,
        ),
        sa.Column(
            "is_ai_flaggable",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.scenario_id"],
            name=op.f("fk_scenario_sheet_rules_scenario_id_scenarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("rule_id", name=op.f("pk_scenario_sheet_rules")),
        sa.UniqueConstraint("scenario_id", "key", name="uq_scenario_sheet_rules_key"),
        sa.UniqueConstraint(
            "scenario_id", "number", name="uq_scenario_sheet_rules_number"
        ),
    )
    op.create_index(
        "idx_scenario_sheet_rules_scenario_id",
        "scenario_sheet_rules",
        ["scenario_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_scenario_sheet_rules_scenario_id", table_name="scenario_sheet_rules"
    )
    op.drop_table("scenario_sheet_rules")

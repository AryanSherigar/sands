"""scenario_rule_checks table

Revision ID: 024_scenario_rule_checks
Revises: 023_condition_sensory_cues

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "024_scenario_rule_checks"
down_revision: str | None = "023_condition_sensory_cues"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.create_table(
        "scenario_rule_checks",
        sa.Column(
            "check_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("scenario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column(
            "trigger_condition_expression",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("result_path", sa.String(length=255), nullable=False),
        sa.Column(
            "params",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("narrator_instruction_template", sa.Text(), nullable=True),
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
            name=op.f("fk_scenario_rule_checks_scenario_id_scenarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("check_id", name=op.f("pk_scenario_rule_checks")),
    )
    op.create_index(
        "idx_scenario_rule_checks_scenario_id",
        "scenario_rule_checks",
        ["scenario_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_scenario_rule_checks_scenario_id", table_name="scenario_rule_checks"
    )
    op.drop_table("scenario_rule_checks")

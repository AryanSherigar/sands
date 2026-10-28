"""Store the shared strategy scenario document.

Revision ID: 036_strategy_scenario_document
Revises: 035_advanced_ui_metadata
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "036_strategy_scenario_document"
down_revision: str | None = "035_advanced_ui_metadata"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

MODE_CONSTRAINT = "ck_scenarios_ck_scenarios_mode"


def upgrade() -> None:
    op.add_column(
        "scenarios",
        sa.Column(
            "strategy_document",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.drop_constraint(op.f(MODE_CONSTRAINT), "scenarios", type_="check")
    op.create_check_constraint(
        op.f(MODE_CONSTRAINT),
        "scenarios",
        "mode IN ('newbie', 'master', 'strategy')",
    )


def downgrade() -> None:
    op.drop_constraint(op.f(MODE_CONSTRAINT), "scenarios", type_="check")
    op.create_check_constraint(
        op.f(MODE_CONSTRAINT),
        "scenarios",
        "mode IN ('newbie', 'master')",
    )
    op.drop_column("scenarios", "strategy_document")

"""scenario_minigames.composure_config

Revision ID: 026_composure_config
Revises: 025_scenario_sheet_rules

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "026_composure_config"
down_revision: str | None = "025_scenario_sheet_rules"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scenario_minigames",
        sa.Column(
            "composure_config",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("scenario_minigames", "composure_config")

"""Strategy mode: the strategy data column holding the traced region map.

Revision ID: 037_strategy_map
Revises: 036_strategy_scenario_document
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "037_strategy_map"
down_revision: str | None = "036_strategy_scenario_document"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

STRATEGY_COLUMN = "strategy_data"


def upgrade() -> None:
    op.add_column(
        "scenarios",
        sa.Column(
            STRATEGY_COLUMN, postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )


def downgrade() -> None:
    op.drop_column("scenarios", STRATEGY_COLUMN)

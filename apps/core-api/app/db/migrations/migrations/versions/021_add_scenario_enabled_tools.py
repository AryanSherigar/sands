"""add scenario enabled_tools

Revision ID: 021_add_scenario_enabled_tools
Revises: 020_add_turn_log_token_usage

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "021_add_scenario_enabled_tools"
down_revision: str | None = "020_add_turn_log_token_usage"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scenarios",
        sa.Column(
            "enabled_tools",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("scenarios", "enabled_tools")

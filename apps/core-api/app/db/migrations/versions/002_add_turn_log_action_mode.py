"""add action_mode to turn_logs

Revision ID: 002_add_turn_log_action_mode
Revises: 001_initial_schema
"""

import sqlalchemy as sa
from alembic import op

revision: str = "002_add_turn_log_action_mode"
down_revision: str | None = "001_initial_schema"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "turn_logs",
        sa.Column(
            "action_mode",
            sa.String(length=16),
            server_default="do",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("turn_logs", "action_mode")

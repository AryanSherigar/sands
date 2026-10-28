"""add turn log token usage

Revision ID: 020_add_turn_log_token_usage
Revises: 019_outbox_participants

"""

import sqlalchemy as sa
from alembic import op

revision: str = "020_add_turn_log_token_usage"
down_revision: str | None = "019_outbox_participants"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "turn_logs",
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "turn_logs",
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
    )
    op.add_column(
        "turn_logs",
        sa.Column("model_name", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("turn_logs", "model_name")
    op.drop_column("turn_logs", "completion_tokens")
    op.drop_column("turn_logs", "prompt_tokens")

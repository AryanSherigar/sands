"""drop replit_embed_url from scenario_minigames

Revision ID: 003_drop_replit_embed_url
Revises: 002_add_turn_log_action_mode
"""

import sqlalchemy as sa
from alembic import op

revision: str = "003_drop_replit_embed_url"
down_revision: str | None = "002_add_turn_log_action_mode"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.execute("DELETE FROM scenario_minigames WHERE minigame_type = 'replit_embed'")
    op.drop_column("scenario_minigames", "replit_embed_url")


def downgrade() -> None:
    op.add_column(
        "scenario_minigames",
        sa.Column("replit_embed_url", sa.String(length=1024), nullable=True),
    )

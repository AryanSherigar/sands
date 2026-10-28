"""Add lockpick_config column to scenario_minigames.

Revision ID: 004_add_lockpick_minigame
Revises: 003_drop_replit_embed_url
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "004_add_lockpick_minigame"
down_revision: str = "003_drop_replit_embed_url"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scenario_minigames",
        sa.Column(
            "lockpick_config",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("scenario_minigames", "lockpick_config")

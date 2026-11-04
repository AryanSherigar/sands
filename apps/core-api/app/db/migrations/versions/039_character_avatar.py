"""Add an optional animated avatar to scenario characters.

Revision ID: 039_character_avatar
Revises: 038_playthrough_initializing
"""

from alembic import op
import sqlalchemy as sa

revision: str = "039_character_avatar"
down_revision: str | None = "038_playthrough_initializing"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column("entities", sa.Column("avatar_url", sa.String(1024), nullable=True))


def downgrade() -> None:
    op.drop_column("entities", "avatar_url")

"""Add expires_at and revoked_at to playthrough_shares.

Revision ID: 006_add_share_token_expiry
Revises: 005_add_voice_output
"""

import sqlalchemy as sa
from alembic import op

revision: str = "006_add_share_token_expiry"
down_revision: str = "005_add_voice_output"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

_SHARE_TOKEN_EXPIRE_DAYS = 30


def upgrade() -> None:
    op.add_column(
        "playthrough_shares",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "playthrough_shares",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        f"UPDATE playthrough_shares SET expires_at = "
        f"created_at + interval '{_SHARE_TOKEN_EXPIRE_DAYS} days' "
        f"WHERE expires_at IS NULL"
    )
    op.alter_column("playthrough_shares", "expires_at", nullable=False)


def downgrade() -> None:
    op.drop_column("playthrough_shares", "revoked_at")
    op.drop_column("playthrough_shares", "expires_at")

"""Remember the previous refresh jti so a lost refresh response can be replayed.

Revision ID: 031_refresh_rotation_grace
Revises: 030_memory_relay_claims
"""

import sqlalchemy as sa
from alembic import op

revision: str = "031_refresh_rotation_grace"
down_revision: str | None = "030_memory_relay_claims"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users", sa.Column("previous_refresh_jti", sa.String(length=36), nullable=True)
    )
    op.add_column(
        "users",
        sa.Column("refresh_rotated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "refresh_rotated_at")
    op.drop_column("users", "previous_refresh_jti")

"""Add users.deletion_requested_at (account deletion grace period marker).

Revision ID: 014_add_user_deletion
Revises: 013_add_show_mature
"""

import sqlalchemy as sa
from alembic import op

revision: str = "014_add_user_deletion"
down_revision: str = "013_add_show_mature"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_users_deletion_requested_at", "users", ["deletion_requested_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_users_deletion_requested_at", table_name="users")
    op.drop_column("users", "deletion_requested_at")

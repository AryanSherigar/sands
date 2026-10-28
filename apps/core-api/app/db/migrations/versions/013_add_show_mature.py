"""Add users.show_mature (saved opt-in to mature stories).

Revision ID: 013_add_show_mature
Revises: 012_add_content_tags
"""

import sqlalchemy as sa
from alembic import op

revision: str = "013_add_show_mature"
down_revision: str = "012_add_content_tags"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "show_mature",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "show_mature")

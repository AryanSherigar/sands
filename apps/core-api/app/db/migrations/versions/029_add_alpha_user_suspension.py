"""Add the alpha user suspension stamp.

Revision ID: 029_add_alpha_user_suspension
Revises: 028_add_alpha_data_collection
"""

import sqlalchemy as sa
from alembic import op

revision: str = "029_add_alpha_user_suspension"
down_revision: str | None = "028_add_alpha_data_collection"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("alpha_suspended_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "alpha_suspended_at")

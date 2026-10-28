"""Add scenarios.content_edited_at and published_content_edited_at.

Revision ID: 015_add_content_edited_at
Revises: 014_add_user_deletion
"""

import sqlalchemy as sa
from alembic import op

revision: str = "015_add_content_edited_at"
down_revision: str = "014_add_user_deletion"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scenarios",
        sa.Column(
            "content_edited_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )
    op.add_column(
        "scenarios",
        sa.Column(
            "published_content_edited_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.execute("UPDATE scenarios SET content_edited_at = updated_at")
    op.execute(
        "UPDATE scenarios SET published_content_edited_at = content_edited_at "
        "WHERE published_at IS NOT NULL"
    )
    op.create_index(
        "ix_scenarios_creator_content_edited",
        "scenarios",
        ["creator_id", "content_edited_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_scenarios_creator_content_edited", table_name="scenarios")
    op.drop_column("scenarios", "published_content_edited_at")
    op.drop_column("scenarios", "content_edited_at")

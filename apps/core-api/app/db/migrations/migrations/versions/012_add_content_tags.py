"""Add scenarios.content_tags (thematic tags, distinct from the age-rating content_tag).

Revision ID: 012_add_content_tags
Revises: 011_add_user_achievements
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "012_add_content_tags"
down_revision: str = "011_add_user_achievements"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scenarios",
        sa.Column(
            "content_tags",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("scenarios", "content_tags")

"""Add user_achievements.

Revision ID: 011_add_user_achievements
Revises: 010_add_ended_outcome_id
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "011_add_user_achievements"
down_revision: str = "010_add_ended_outcome_id"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_achievements",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.user_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("achievement_key", sa.String(length=64), primary_key=True),
        sa.Column(
            "earned_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("user_achievements")

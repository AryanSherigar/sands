"""Add users.onboarding_completed_at and users.preferred_genres.

Existing users are backfilled as onboarded so only new signups see the wizard.

Revision ID: 007_add_onboarding
Revises: 006_add_share_token_expiry
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "007_add_onboarding"
down_revision: str = "006_add_share_token_expiry"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("onboarding_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "preferred_genres",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
    )
    op.execute("UPDATE users SET onboarding_completed_at = now()")


def downgrade() -> None:
    op.drop_column("users", "preferred_genres")
    op.drop_column("users", "onboarding_completed_at")

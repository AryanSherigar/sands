"""Add playtime bucket and mature flag for discovery filtering.

Revision ID: 009_add_discovery_filters
Revises: 008_add_creator_stats_indexes
"""

import sqlalchemy as sa
from alembic import op

revision: str = "009_add_discovery_filters"
down_revision: str = "008_add_creator_stats_indexes"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

_BUCKET_CONSTRAINT = "ck_scenarios_playtime_bucket"


def upgrade() -> None:
    op.add_column(
        "scenarios", sa.Column("playtime_bucket", sa.String(length=10), nullable=True)
    )
    op.create_check_constraint(
        _BUCKET_CONSTRAINT,
        "scenarios",
        "playtime_bucket IN ('short', 'medium', 'long')",
    )
    op.add_column(
        "scenarios",
        sa.Column("is_mature", sa.Boolean(), server_default=sa.false(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("scenarios", "is_mature")
    op.drop_constraint(_BUCKET_CONSTRAINT, "scenarios", type_="check")
    op.drop_column("scenarios", "playtime_bucket")

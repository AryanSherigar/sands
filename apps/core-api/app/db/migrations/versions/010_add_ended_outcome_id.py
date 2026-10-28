"""Add ended_outcome_id to playthroughs.

Revision ID: 010_add_ended_outcome_id
Revises: 009_add_discovery_filters
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "010_add_ended_outcome_id"
down_revision: str = "009_add_discovery_filters"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "playthroughs",
        sa.Column("ended_outcome_id", postgresql.UUID(as_uuid=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("playthroughs", "ended_outcome_id")

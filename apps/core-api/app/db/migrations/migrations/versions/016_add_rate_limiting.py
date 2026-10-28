"""Add rate_limit_counters and rate_limit_stream_leases.

Revision ID: 016_add_rate_limiting
Revises: 015_add_content_edited_at
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "016_add_rate_limiting"
down_revision: str = "015_add_content_edited_at"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_counters",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("window_start", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("key", "window_start", name="pk_rate_limit_counters"),
    )
    op.create_index(
        "ix_rate_limit_counters_expires_at", "rate_limit_counters", ["expires_at"]
    )
    op.create_table(
        "rate_limit_stream_leases",
        sa.Column(
            "lease_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("subject_key", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("lease_id", name="pk_rate_limit_stream_leases"),
    )
    op.create_index(
        "ix_rate_limit_stream_leases_subject_expires",
        "rate_limit_stream_leases",
        ["subject_key", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_rate_limit_stream_leases_subject_expires",
        table_name="rate_limit_stream_leases",
    )
    op.drop_table("rate_limit_stream_leases")
    op.drop_index("ix_rate_limit_counters_expires_at", table_name="rate_limit_counters")
    op.drop_table("rate_limit_counters")

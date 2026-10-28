"""Add durable relay claims without changing existing outbox rows.

Revision ID: 030_memory_relay_claims
Revises: 029_add_alpha_user_suspension
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "030_memory_relay_claims"
down_revision: str | None = "029_add_alpha_user_suspension"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.create_table(
        "memory_relay_claims",
        sa.Column("playthrough_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("delivery_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ownership_token", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outbox_ids", postgresql.ARRAY(sa.BigInteger()), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("memory_relay_claims")

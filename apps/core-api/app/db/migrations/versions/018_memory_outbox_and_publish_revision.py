"""Add memory_outbox, publish revision pinning, and turn accepted_delta.

Revision ID: 018_memory_outbox
Revises: 017_unique_share_per_mode
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "018_memory_outbox"
down_revision: str = "017_unique_share_per_mode"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

CLIENT_ACTION_CONSTRAINT = "uq_turn_logs_playthrough_client_action"


def _create_memory_outbox_table() -> None:
    op.create_table(
        "memory_outbox",
        sa.Column("outbox_id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("playthrough_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_kind", sa.String(length=32), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("delivered_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "item_kind IN ('register_playthrough', 'turn', 'flush')",
            name=op.f("ck_memory_outbox_item_kind"),
        ),
        sa.PrimaryKeyConstraint("outbox_id", name="pk_memory_outbox"),
        sa.UniqueConstraint(
            "playthrough_id",
            "item_kind",
            "sequence",
            name="uq_memory_outbox_playthrough_kind_sequence",
        ),
    )


def _create_memory_outbox_index() -> None:
    op.create_index(
        "ix_memory_outbox_undelivered",
        "memory_outbox",
        ["playthrough_id", "sequence"],
        postgresql_where=sa.text("delivered_at IS NULL"),
    )


def _add_revision_and_delta_columns() -> None:
    op.add_column(
        "scenarios",
        sa.Column("publish_revision", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "playthroughs",
        sa.Column("memory_publish_revision", sa.Integer(), nullable=True),
    )
    op.add_column(
        "turn_logs",
        sa.Column(
            "accepted_delta",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
    )
    op.add_column(
        "turn_logs",
        sa.Column("client_action_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_unique_constraint(
        CLIENT_ACTION_CONSTRAINT,
        "turn_logs",
        ["playthrough_id", "client_action_id"],
    )


def upgrade() -> None:
    _create_memory_outbox_table()
    _create_memory_outbox_index()
    _add_revision_and_delta_columns()


def downgrade() -> None:
    op.drop_constraint(CLIENT_ACTION_CONSTRAINT, "turn_logs", type_="unique")
    op.drop_column("turn_logs", "client_action_id")
    op.drop_column("turn_logs", "accepted_delta")
    op.drop_column("playthroughs", "memory_publish_revision")
    op.drop_column("scenarios", "publish_revision")
    op.drop_index("ix_memory_outbox_undelivered", table_name="memory_outbox")
    op.drop_table("memory_outbox")

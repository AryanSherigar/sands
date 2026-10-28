"""Add alpha_invites, alpha_invite_redemptions and user alpha consent columns.

Revision ID: 027_add_alpha_perimeter
Revises: 026_composure_config
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "027_add_alpha_perimeter"
down_revision: str | None = "026_composure_config"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alpha_invites",
        sa.Column(
            "invite_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code_hash", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("max_seats", sa.Integer(), nullable=False),
        sa.Column("seats_used", sa.Integer(), server_default="0", nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("max_seats >= 1", name="max_seats_positive"),
        sa.CheckConstraint("seats_used <= max_seats", name="seats_within_max"),
        sa.PrimaryKeyConstraint("invite_id", name="pk_alpha_invites"),
        sa.UniqueConstraint("code_hash", name="uq_alpha_invites_code_hash"),
    )
    op.create_table(
        "alpha_invite_redemptions",
        sa.Column(
            "redemption_id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("invite_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "redeemed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["invite_id"],
            ["alpha_invites.invite_id"],
            name="fk_alpha_invite_redemptions_invite_id_alpha_invites",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name="fk_alpha_invite_redemptions_user_id_users",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("redemption_id", name="pk_alpha_invite_redemptions"),
        sa.UniqueConstraint("user_id", name="uq_alpha_invite_redemptions_user_id"),
    )
    op.add_column("users", sa.Column("alpha_consent_version", sa.Text(), nullable=True))
    op.add_column(
        "users",
        sa.Column("alpha_consented_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "alpha_consented_at")
    op.drop_column("users", "alpha_consent_version")
    op.drop_table("alpha_invite_redemptions")
    op.drop_table("alpha_invites")

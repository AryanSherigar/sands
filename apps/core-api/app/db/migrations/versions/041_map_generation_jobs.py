"""Add map_generation_jobs for background strategy map generation.

Revision ID: 041_map_generation_jobs
Revises: 040_published_strategy_document
"""

from alembic import op
import sqlalchemy as sa

revision: str = "041_map_generation_jobs"
down_revision: str | None = "040_published_strategy_document"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.create_table(
        "map_generation_jobs",
        sa.Column(
            "job_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("creator_id", sa.UUID(), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="pending", nullable=False
        ),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("region_image_url", sa.String(length=2048), nullable=True),
        sa.Column("picture_url", sa.String(length=2048), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column(
            "has_art", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('pending','running','succeeded','failed')",
            name=op.f("ck_map_generation_jobs_ck_map_generation_jobs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.user_id"],
            name=op.f("fk_map_generation_jobs_creator_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.scenario_id"],
            name=op.f("fk_map_generation_jobs_scenario_id_scenarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("job_id", name=op.f("pk_map_generation_jobs")),
    )
    op.create_index(
        "ix_map_generation_jobs_scenario_created",
        "map_generation_jobs",
        ["scenario_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_map_generation_jobs_scenario_created", table_name="map_generation_jobs"
    )
    op.drop_table("map_generation_jobs")

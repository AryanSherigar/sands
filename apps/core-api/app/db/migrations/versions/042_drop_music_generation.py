"""Drop Lyria music generation tables.

Revision ID: 042_drop_music_generation
Revises: 041_map_generation_jobs
"""

from alembic import op
import sqlalchemy as sa

revision: str = "042_drop_music_generation"
down_revision: str | None = "041_map_generation_jobs"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.drop_table("music_generation_log")
    op.drop_table("music_generation_jobs")


def downgrade() -> None:
    op.create_table(
        "music_generation_jobs",
        sa.Column(
            "job_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("creator_id", sa.UUID(), nullable=False),
        sa.Column("mood", sa.String(length=20), nullable=False),
        sa.Column(
            "status", sa.String(length=20), server_default="pending", nullable=False
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("preview_url", sa.String(length=2048), nullable=True),
        sa.Column("key", sa.String(length=20), nullable=True),
        sa.Column("bpm", sa.Integer(), nullable=True),
        sa.Column("duration_seconds", sa.Numeric(precision=6, scale=2), nullable=True),
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
            name=op.f("ck_music_generation_jobs_ck_music_generation_jobs_status"),
        ),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.user_id"],
            name=op.f("fk_music_generation_jobs_creator_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.scenario_id"],
            name=op.f("fk_music_generation_jobs_scenario_id_scenarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("job_id", name=op.f("pk_music_generation_jobs")),
    )
    op.create_table(
        "music_generation_log",
        sa.Column(
            "log_id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("creator_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["creator_id"],
            ["users.user_id"],
            name=op.f("fk_music_generation_log_creator_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.scenario_id"],
            name=op.f("fk_music_generation_log_scenario_id_scenarios"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("log_id", name=op.f("pk_music_generation_log")),
    )

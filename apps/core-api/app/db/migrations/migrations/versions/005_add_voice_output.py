"""Add voice output columns: turn_logs.audio_url, scenarios.narrator_voice_name,
users.voice_output_enabled.

Revision ID: 005_add_voice_output
Revises: 004_add_lockpick_minigame
"""

import sqlalchemy as sa
from alembic import op

revision: str = "005_add_voice_output"
down_revision: str = "004_add_lockpick_minigame"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "turn_logs", sa.Column("audio_url", sa.String(length=1024), nullable=True)
    )
    op.add_column(
        "scenarios",
        sa.Column("narrator_voice_name", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "voice_output_enabled",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "voice_output_enabled")
    op.drop_column("scenarios", "narrator_voice_name")
    op.drop_column("turn_logs", "audio_url")

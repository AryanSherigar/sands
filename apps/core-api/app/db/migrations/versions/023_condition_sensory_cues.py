"""condition sensory cue columns

Revision ID: 023_condition_sensory_cues
Revises: 022_condition_authoring_ext

"""

import sqlalchemy as sa
from alembic import op

revision: str = "023_condition_sensory_cues"
down_revision: str | None = "022_condition_authoring_ext"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scenario_conditions",
        sa.Column("sensory_cue", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "scenario_conditions",
        sa.Column(
            "cut_ambient",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
    )
    op.add_column(
        "scenario_conditions",
        sa.Column(
            "silence_duration_ms",
            sa.Integer(),
            server_default="800",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("scenario_conditions", "silence_duration_ms")
    op.drop_column("scenario_conditions", "cut_ambient")
    op.drop_column("scenario_conditions", "sensory_cue")

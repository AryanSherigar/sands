"""condition mutation lists, fire-once flag and minigame outcome mutation lists

Revision ID: 022_condition_authoring_ext
Revises: 021_add_scenario_enabled_tools

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "022_condition_authoring_ext"
down_revision: str | None = "021_add_scenario_enabled_tools"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

_EMPTY_LIST = sa.text("'[]'::jsonb")
_MINIGAME_LIST_COLUMNS = ("win_mutations", "lose_mutations", "timeout_mutations")


def upgrade() -> None:
    op.add_column(
        "scenario_conditions",
        sa.Column(
            "state_mutations",
            postgresql.JSONB(),
            server_default=_EMPTY_LIST,
            nullable=False,
        ),
    )
    op.add_column(
        "scenario_conditions",
        sa.Column(
            "is_one_shot",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )
    for column in _MINIGAME_LIST_COLUMNS:
        op.add_column(
            "scenario_minigames",
            sa.Column(
                column, postgresql.JSONB(), server_default=_EMPTY_LIST, nullable=False
            ),
        )


def downgrade() -> None:
    for column in reversed(_MINIGAME_LIST_COLUMNS):
        op.drop_column("scenario_minigames", column)
    op.drop_column("scenario_conditions", "is_one_shot")
    op.drop_column("scenario_conditions", "state_mutations")

"""Add indexes backing creator stats aggregation.

Revision ID: 008_add_creator_stats_indexes
Revises: 007_add_onboarding
"""

from alembic import op

revision: str = "008_add_creator_stats_indexes"
down_revision: str = "007_add_onboarding"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

_INDEXES: list[tuple[str, str, list[str]]] = [
    (
        "idx_playthroughs_scenario_created_at",
        "playthroughs",
        ["scenario_id", "created_at"],
    ),
    (
        "idx_scenario_reviews_scenario_created_at",
        "scenario_reviews",
        ["scenario_id", "created_at"],
    ),
    ("idx_bookmarks_scenario_id", "bookmarks", ["scenario_id"]),
    ("idx_playthrough_shares_playthrough_id", "playthrough_shares", ["playthrough_id"]),
]


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        op.create_index(name, table, columns, unique=False)


def downgrade() -> None:
    for name, table, _columns in reversed(_INDEXES):
        op.drop_index(name, table_name=table)

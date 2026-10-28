"""Strategy mode: playthroughs may wait in an 'initializing' status.

Revision ID: 038_playthrough_initializing
Revises: 037_strategy_map
"""

from alembic import op

revision: str = "038_playthrough_initializing"
down_revision: str | None = "037_strategy_map"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

CONSTRAINT = "ck_playthroughs_ck_playthroughs_status"
OLD_STATUSES = "status IN ('active', 'completed', 'abandoned')"
NEW_STATUSES = "status IN ('initializing', 'active', 'completed', 'abandoned')"


def upgrade() -> None:
    op.drop_constraint(op.f(CONSTRAINT), "playthroughs", type_="check")
    op.create_check_constraint(op.f(CONSTRAINT), "playthroughs", NEW_STATUSES)


def downgrade() -> None:
    op.drop_constraint(op.f(CONSTRAINT), "playthroughs", type_="check")
    op.create_check_constraint(op.f(CONSTRAINT), "playthroughs", OLD_STATUSES)

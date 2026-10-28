"""Enforce one share row per (playthrough_id, mode).

Revision ID: 017_unique_share_per_mode
Revises: 016_add_rate_limiting
"""

from alembic import op

revision: str = "017_unique_share_per_mode"
down_revision: str = "016_add_rate_limiting"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

CONSTRAINT_NAME = "uq_playthrough_shares_playthrough_mode"

DELETE_DUPLICATE_SHARES_SQL = """
DELETE FROM playthrough_shares
WHERE share_id IN (
    SELECT share_id FROM (
        SELECT
            share_id,
            ROW_NUMBER() OVER (
                PARTITION BY playthrough_id, mode
                ORDER BY
                    (revoked_at IS NULL AND expires_at > now()) DESC,
                    created_at DESC,
                    share_id DESC
            ) AS row_rank
        FROM playthrough_shares
    ) ranked
    WHERE ranked.row_rank > 1
)
"""


def upgrade() -> None:
    # TRADE-OFF: Duplicates only arose from concurrent create_share calls.
    # Keeping the newest still-valid row preserves the link most likely in
    # use; a URL built from a discarded duplicate stops resolving.
    op.execute(DELETE_DUPLICATE_SHARES_SQL)
    op.create_unique_constraint(
        CONSTRAINT_NAME, "playthrough_shares", ["playthrough_id", "mode"]
    )


def downgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, "playthrough_shares", type_="unique")

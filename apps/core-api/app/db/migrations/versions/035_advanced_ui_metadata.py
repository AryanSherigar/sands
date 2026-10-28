"""Advanced mode: opaque UI metadata on end conditions and rule invariants.

The Studio stores the sentence builder's wording choices (for example
"drops to" versus "is at most", which compile to the same expression) beside
the row. The column is nullable and never read by the engine.

Revision ID: 035_advanced_ui_metadata
Revises: 034_guided_creation
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "035_advanced_ui_metadata"
down_revision: str | None = "034_guided_creation"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

TABLES = ("end_conditions", "rule_invariants")
METADATA_COLUMN = "metadata"


def upgrade() -> None:
    for table in TABLES:
        op.add_column(
            table,
            sa.Column(
                METADATA_COLUMN, postgresql.JSONB(astext_type=sa.Text()), nullable=True
            ),
        )


def downgrade() -> None:
    for table in TABLES:
        op.drop_column(table, METADATA_COLUMN)

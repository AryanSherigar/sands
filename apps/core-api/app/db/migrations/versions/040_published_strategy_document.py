"""Pin the strategy document a scenario was last published with.

Revision ID: 040_published_strategy_document
Revises: 039_character_avatar
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "040_published_strategy_document"
down_revision: str | None = "039_character_avatar"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scenarios",
        sa.Column(
            "published_strategy_document",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.execute(
        "UPDATE scenarios SET published_strategy_document = strategy_document "
        "WHERE mode = 'strategy' AND published_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_column("scenarios", "published_strategy_document")

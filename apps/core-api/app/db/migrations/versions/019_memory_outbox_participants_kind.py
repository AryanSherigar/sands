"""Allow the participants item kind on memory_outbox.

Revision ID: 019_outbox_participants
Revises: 018_memory_outbox
"""

import sqlalchemy as sa
from alembic import op

revision: str = "019_outbox_participants"
down_revision: str = "018_memory_outbox"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

CONSTRAINT_NAME = "ck_memory_outbox_item_kind"
KINDS_BEFORE = "item_kind IN ('register_playthrough', 'turn', 'flush')"
KINDS_AFTER = "item_kind IN ('register_playthrough', 'turn', 'participants', 'flush')"


def upgrade() -> None:
    op.drop_constraint(op.f(CONSTRAINT_NAME), "memory_outbox", type_="check")
    op.create_check_constraint(
        op.f(CONSTRAINT_NAME), "memory_outbox", sa.text(KINDS_AFTER)
    )


def downgrade() -> None:
    op.execute("DELETE FROM memory_outbox WHERE item_kind = 'participants'")
    op.drop_constraint(op.f(CONSTRAINT_NAME), "memory_outbox", type_="check")
    op.create_check_constraint(
        op.f(CONSTRAINT_NAME), "memory_outbox", sa.text(KINDS_BEFORE)
    )

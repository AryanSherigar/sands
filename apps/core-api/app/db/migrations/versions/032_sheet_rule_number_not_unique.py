"""Allow two sheet rules to share a number.

A scenario may author alternate rows for one printed rule (Night Desk's rule 6
is written in one of two hands, chosen per playthrough). `key` stays unique.

Revision ID: 032_sheet_rule_number_not_unique
Revises: 031_refresh_rotation_grace
"""

import sqlalchemy as sa
from alembic import op

revision: str = "032_sheet_rule_number_not_unique"
down_revision: str | None = "031_refresh_rotation_grace"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

CONSTRAINT_NAME = "uq_scenario_sheet_rules_number"
TABLE_NAME = "scenario_sheet_rules"


def upgrade() -> None:
    op.drop_constraint(CONSTRAINT_NAME, TABLE_NAME, type_="unique")


def downgrade() -> None:
    shared = (
        op.get_bind()
        .execute(
            sa.text(
                "SELECT count(*) FROM (SELECT 1 FROM scenario_sheet_rules "
                "GROUP BY scenario_id, number HAVING count(*) > 1) AS shared"
            )
        )
        .scalar_one()
    )
    if shared:
        raise RuntimeError(
            "Cannot restore uq_scenario_sheet_rules_number: "
            f"{shared} scenario(s) have two sheet rules with one number. "
            "Renumber or delete the alternate rows first."
        )
    op.create_unique_constraint(CONSTRAINT_NAME, TABLE_NAME, ["scenario_id", "number"])

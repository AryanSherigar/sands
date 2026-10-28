"""Add private scenarios: a visibility column and a per-scenario allowlist.

A private scenario is readable and playable only by its creator and the users in
scenario_access. Existing scenarios stay public.

Revision ID: 033_private_scenarios
Revises: 032_sheet_rule_number_not_unique
"""

import sqlalchemy as sa
from alembic import op

revision: str = "033_private_scenarios"
down_revision: str | None = "032_sheet_rule_number_not_unique"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None

CONSTRAINT_NAME = "ck_scenarios_visibility"
ACCESS_TABLE = "scenario_access"


def upgrade() -> None:
    op.add_column(
        "scenarios",
        sa.Column(
            "visibility", sa.String(length=10), server_default="public", nullable=False
        ),
    )
    op.create_check_constraint(
        op.f(CONSTRAINT_NAME),
        "scenarios",
        sa.text("visibility IN ('public', 'private')"),
    )
    op.create_table(
        ACCESS_TABLE,
        sa.Column("scenario_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["scenario_id"],
            ["scenarios.scenario_id"],
            name=op.f("fk_scenario_access_scenario_id_scenarios"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.user_id"],
            name=op.f("fk_scenario_access_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "scenario_id", "user_id", name=op.f("pk_scenario_access")
        ),
    )
    op.create_index("idx_scenario_access_user_id", ACCESS_TABLE, ["user_id"])


def downgrade() -> None:
    private = (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM scenarios WHERE visibility = 'private'"))
        .scalar_one()
    )
    if private:
        raise RuntimeError(
            f"Cannot drop visibility: {private} private scenario(s) would become "
            "public. Make them public or delete them first."
        )
    op.drop_index("idx_scenario_access_user_id", table_name=ACCESS_TABLE)
    op.drop_table(ACCESS_TABLE)
    op.drop_constraint(op.f(CONSTRAINT_NAME), "scenarios", type_="check")
    op.drop_column("scenarios", "visibility")

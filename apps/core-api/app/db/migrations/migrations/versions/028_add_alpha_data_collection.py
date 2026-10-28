"""Add alpha data collection tables.

Revision ID: 028_add_alpha_data_collection
Revises: 027_add_alpha_perimeter
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "028_add_alpha_data_collection"
down_revision: str | None = "027_add_alpha_perimeter"
branch_labels: list[str] | None = None
depends_on: list[str] | None = None


def _uuid_pk(name: str) -> sa.Column:
    return sa.Column(
        name,
        postgresql.UUID(as_uuid=True),
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def _created_at() -> sa.Column:
    return sa.Column(
        "created_at",
        sa.TIMESTAMP(timezone=True),
        server_default=sa.text("CURRENT_TIMESTAMP"),
        nullable=False,
    )


def _user_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["user_id"],
        ["users.user_id"],
        name=f"fk_{table}_user_id_users",
        ondelete="CASCADE",
    )


def _playthrough_fk(table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        ["playthrough_id"],
        ["playthroughs.playthrough_id"],
        name=f"fk_{table}_playthrough_id_playthroughs",
        ondelete="CASCADE",
    )


def _create_turn_metrics() -> None:
    uuid_type = postgresql.UUID(as_uuid=True)
    empty_text_array = sa.text("'{}'::text[]")
    op.create_table(
        "turn_metrics",
        sa.Column("turn_id", uuid_type, nullable=False),
        sa.Column("playthrough_id", uuid_type, nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=False),
        sa.Column("first_token_ms", sa.Integer(), nullable=True),
        sa.Column("generation_ms", sa.Integer(), nullable=True),
        sa.Column("total_ms", sa.Integer(), nullable=False),
        sa.Column("step_durations", postgresql.JSONB(), nullable=False),
        sa.Column(
            "memory_degraded_reasons",
            postgresql.ARRAY(sa.Text()),
            server_default=empty_text_array,
            nullable=False,
        ),
        sa.Column("memory_retrieval_ms", sa.Integer(), nullable=True),
        sa.Column("memory_facts_returned", sa.Integer(), nullable=True),
        sa.Column(
            "fired_condition_ids",
            postgresql.ARRAY(sa.Text()),
            server_default=empty_text_array,
            nullable=False,
        ),
        sa.Column(
            "dropped_mutation_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column(
            "dropped_mutation_paths",
            postgresql.ARRAY(sa.Text()),
            server_default=empty_text_array,
            nullable=False,
        ),
        sa.Column(
            "check_outcomes",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "stat_snapshot",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("replay_count", sa.Integer(), server_default="0", nullable=False),
        _created_at(),
        sa.ForeignKeyConstraint(
            ["turn_id"],
            ["turn_logs.turn_id"],
            name="fk_turn_metrics_turn_id_turn_logs",
            ondelete="CASCADE",
        ),
        _playthrough_fk("turn_metrics"),
        sa.PrimaryKeyConstraint("turn_id", name="pk_turn_metrics"),
    )


def _create_alpha_events() -> None:
    op.create_table(
        "alpha_events",
        _uuid_pk("event_id"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("playthrough_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("session_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "props",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("client_ts", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "received_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("source IN ('client', 'server')", name="source"),
        _user_fk("alpha_events"),
        _playthrough_fk("alpha_events"),
        sa.PrimaryKeyConstraint("event_id", name="pk_alpha_events"),
    )
    op.create_index(
        "ix_alpha_events_user_id_received_at",
        "alpha_events",
        ["user_id", "received_at"],
    )
    op.create_index(
        "ix_alpha_events_name_received_at", "alpha_events", ["name", "received_at"]
    )


def _create_alpha_feedback() -> None:
    op.create_table(
        "alpha_feedback",
        _uuid_pk("feedback_id"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("playthrough_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_number", sa.Integer(), nullable=True),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        _created_at(),
        sa.CheckConstraint(
            "category IN ('bug', 'confusing', 'scary', 'other')", name="category"
        ),
        sa.CheckConstraint("char_length(body) <= 2000", name="body_length"),
        _user_fk("alpha_feedback"),
        _playthrough_fk("alpha_feedback"),
        sa.PrimaryKeyConstraint("feedback_id", name="pk_alpha_feedback"),
    )


def _create_alpha_narration_flags() -> None:
    op.create_table(
        "alpha_narration_flags",
        _uuid_pk("flag_id"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("playthrough_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turn_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "reasons",
            postgresql.ARRAY(sa.Text()),
            server_default=sa.text("'{}'::text[]"),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        _created_at(),
        _user_fk("alpha_narration_flags"),
        _playthrough_fk("alpha_narration_flags"),
        sa.ForeignKeyConstraint(
            ["turn_id"],
            ["turn_logs.turn_id"],
            name="fk_alpha_narration_flags_turn_id_turn_logs",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("flag_id", name="pk_alpha_narration_flags"),
        sa.UniqueConstraint(
            "user_id", "turn_id", name="uq_alpha_narration_flags_user_turn"
        ),
    )


def _create_alpha_survey_responses() -> None:
    op.create_table(
        "alpha_survey_responses",
        _uuid_pk("response_id"),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("playthrough_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("answers", postgresql.JSONB(), nullable=False),
        _created_at(),
        sa.CheckConstraint("kind IN ('intake', 'post_run')", name="kind"),
        _user_fk("alpha_survey_responses"),
        _playthrough_fk("alpha_survey_responses"),
        sa.PrimaryKeyConstraint("response_id", name="pk_alpha_survey_responses"),
    )
    op.create_index(
        "uq_alpha_survey_responses_intake",
        "alpha_survey_responses",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'intake'"),
    )
    op.create_index(
        "uq_alpha_survey_responses_post_run",
        "alpha_survey_responses",
        ["user_id", "playthrough_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'post_run'"),
    )


def upgrade() -> None:
    _create_turn_metrics()
    _create_alpha_events()
    _create_alpha_feedback()
    _create_alpha_narration_flags()
    _create_alpha_survey_responses()


def downgrade() -> None:
    op.drop_table("alpha_survey_responses")
    op.drop_table("alpha_narration_flags")
    op.drop_table("alpha_feedback")
    op.drop_table("alpha_events")
    op.drop_table("turn_metrics")

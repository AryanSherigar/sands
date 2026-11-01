"""Pure eligibility context construction."""

from uuid import uuid4

import pytest
from app.models.eligibility import EligibilityContext
from app.services.eligibility import build_eligibility_context
from pydantic import ValidationError


def test_builds_a_frozen_context_from_plain_inputs() -> None:
    playthrough_id, template_id = uuid4(), uuid4()
    revealed, active = uuid4(), uuid4()

    ctx = build_eligibility_context(
        playthrough_id=playthrough_id,
        template_id=template_id,
        at_seq=12,
        recent_window_turns=6,
        revealed_fact_ids=[revealed],
        active_conditional_fact_ids=[active],
    )

    assert ctx.playthrough_id == playthrough_id
    assert ctx.template_id == template_id
    assert ctx.at_seq == 12
    assert ctx.recent_window_turns == 6
    assert ctx.revealed_authored_fact_ids == [revealed]
    assert ctx.active_conditional_authored_fact_ids == [active]
    assert ctx.should_include_hidden is False
    with pytest.raises(ValidationError):
        ctx.at_seq = 1  # type: ignore[misc]


def test_null_template_and_include_hidden_pass_through() -> None:
    ctx = build_eligibility_context(
        playthrough_id=uuid4(),
        template_id=None,
        at_seq=0,
        recent_window_turns=0,
        revealed_fact_ids=[],
        active_conditional_fact_ids=[],
        should_include_hidden=True,
    )

    assert ctx.template_id is None
    assert ctx.should_include_hidden is True


def test_duplicate_ids_are_collapsed_keeping_first_seen_order() -> None:
    first, second = uuid4(), uuid4()

    ctx = build_eligibility_context(
        playthrough_id=uuid4(),
        template_id=None,
        at_seq=3,
        recent_window_turns=1,
        revealed_fact_ids=[first, second, first],
        active_conditional_fact_ids=[second, second],
    )

    assert ctx.revealed_authored_fact_ids == [first, second]
    assert ctx.active_conditional_authored_fact_ids == [second]


def test_negative_sequence_or_window_is_rejected() -> None:
    with pytest.raises(ValidationError):
        build_eligibility_context(
            playthrough_id=uuid4(),
            template_id=None,
            at_seq=-1,
            recent_window_turns=0,
            revealed_fact_ids=[],
            active_conditional_fact_ids=[],
        )
    with pytest.raises(ValidationError):
        build_eligibility_context(
            playthrough_id=uuid4(),
            template_id=None,
            at_seq=1,
            recent_window_turns=-1,
            revealed_fact_ids=[],
            active_conditional_fact_ids=[],
        )


def test_to_params_names_every_parameter_the_sql_fragments_use() -> None:
    ctx = EligibilityContext(
        playthrough_id=uuid4(), template_id=None, at_seq=4, recent_window_turns=2
    )

    params = ctx.to_params()

    assert set(params) == {
        "playthrough_id",
        "template_id",
        "at_seq",
        "recent_window_turns",
        "revealed_authored_fact_ids",
        "active_conditional_authored_fact_ids",
        "should_include_hidden",
    }
    assert params["template_id"] is None
    assert params["revealed_authored_fact_ids"] == []

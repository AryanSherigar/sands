"""Pure construction of the retrieval eligibility context."""

from uuid import UUID

from app.models.eligibility import EligibilityContext


def _deduplicate(ids: list[UUID]) -> list[UUID]:
    return list(dict.fromkeys(ids))


def build_eligibility_context(
    *,
    playthrough_id: UUID,
    template_id: UUID | None,
    at_seq: int,
    recent_window_turns: int,
    revealed_fact_ids: list[UUID],
    active_conditional_fact_ids: list[UUID],
    should_include_hidden: bool = False,
) -> EligibilityContext:
    """`template_id` comes from the registered playthrough row, never from the
    request, so a caller cannot choose its own scope."""
    return EligibilityContext(
        playthrough_id=playthrough_id,
        template_id=template_id,
        at_seq=at_seq,
        recent_window_turns=recent_window_turns,
        revealed_authored_fact_ids=_deduplicate(revealed_fact_ids),
        active_conditional_authored_fact_ids=_deduplicate(active_conditional_fact_ids),
        should_include_hidden=should_include_hidden,
    )

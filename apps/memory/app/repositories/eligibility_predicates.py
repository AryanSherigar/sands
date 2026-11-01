"""SQL fragments composed into every retrieval query. Named parameters come from
`EligibilityContext.to_params()`; commitments also need
`commitment_recent_resolution_turns`.

Aliases are fixed: `span`, `fact`, `commitment` (with `latest_status`). A fact is
eligible only when both of its entity endpoints are in scope too. Every fragment is
a boolean expression that is never NULL, so a missing policy input excludes the row.
"""

TURN_SOURCE_KINDS = "('turn_action', 'turn_narration')"

_SCOPE_TEMPLATE = """(
    (
        {alias}.scope_kind = 'template'
        AND %(template_id)s::uuid IS NOT NULL
        AND {alias}.scope_id = %(template_id)s::uuid
    )
    OR (
        {alias}.scope_kind = 'playthrough'
        AND {alias}.scope_id = %(playthrough_id)s::uuid
    )
)"""

_HIDDEN_TEMPLATE = """(
    NOT {alias}.is_hidden
    OR (
        {alias}.authored_fact_id IS NOT NULL
        AND (
            %(should_include_hidden)s::boolean
            OR {alias}.authored_fact_id = ANY(%(revealed_authored_fact_ids)s::uuid[])
        )
    )
)"""

_CONDITIONAL_TEMPLATE = """(
    NOT {alias}.conditional
    OR (
        {alias}.authored_fact_id IS NOT NULL
        AND {alias}.authored_fact_id
            = ANY(%(active_conditional_authored_fact_ids)s::uuid[])
    )
)"""

_FACT_VALID_TEMPLATE = """(
    {alias}.valid_from_seq <= %(at_seq)s::integer
    AND NOT EXISTS (
        SELECT 1 FROM memory_supersession AS {alias}_supersession
        WHERE {alias}_supersession.playthrough_id = %(playthrough_id)s::uuid
            AND {alias}_supersession.fact_id = {alias}.fact_id
            AND {alias}_supersession.at_seq <= %(at_seq)s::integer
    )
)"""

_SUCCESSOR_ELIGIBLE = " AND ".join(
    template.format(alias="successor")
    for template in (_FACT_VALID_TEMPLATE, _HIDDEN_TEMPLATE, _CONDITIONAL_TEMPLATE)
)

_AUTHORED_SUPERSESSION_TEMPLATE = """NOT (
    {alias}.scope_kind = 'template'
    AND {alias}.authored_fact_id IS NOT NULL
    AND EXISTS (
        SELECT 1 FROM memory_fact AS successor
        WHERE successor.scope_kind = 'template'
            AND successor.scope_id = {alias}.scope_id
            AND successor.supersedes_authored_fact_id = {alias}.authored_fact_id
            AND {successor_eligible}
    )
)"""

SPAN_WINDOW_PREDICATE = f"""EXISTS (
    SELECT 1 FROM memory_source AS span_source
    WHERE span_source.source_id = span.source_id
        AND (
            span_source.source_kind NOT IN {TURN_SOURCE_KINDS}
            OR span.sequence
                <= %(at_seq)s::integer - %(recent_window_turns)s::integer
        )
)"""


def scope_predicate(alias: str) -> str:
    return _SCOPE_TEMPLATE.format(alias=alias)


SPAN_SCOPE_PREDICATE = scope_predicate("span")
FACT_SCOPE_PREDICATE = scope_predicate("fact")

FACT_VALID_PREDICATE = _FACT_VALID_TEMPLATE.format(alias="fact")

SPAN_ELIGIBLE = " AND ".join(
    (
        SPAN_SCOPE_PREDICATE,
        SPAN_WINDOW_PREDICATE,
        _HIDDEN_TEMPLATE.format(alias="span"),
        _CONDITIONAL_TEMPLATE.format(alias="span"),
        _AUTHORED_SUPERSESSION_TEMPLATE.format(
            alias="span", successor_eligible=_SUCCESSOR_ELIGIBLE
        ),
    )
)

FACT_ENDPOINTS_IN_SCOPE = f"""(
    EXISTS (
        SELECT 1 FROM memory_entity AS subject_entity
        WHERE subject_entity.entity_id = fact.subject_entity_id
            AND {scope_predicate("subject_entity")}
    )
    AND (
        fact.object_entity_id IS NULL
        OR EXISTS (
            SELECT 1 FROM memory_entity AS object_entity
            WHERE object_entity.entity_id = fact.object_entity_id
                AND {scope_predicate("object_entity")}
        )
    )
)"""

FACT_ELIGIBLE = " AND ".join(
    (
        FACT_SCOPE_PREDICATE,
        FACT_VALID_PREDICATE,
        _HIDDEN_TEMPLATE.format(alias="fact"),
        _CONDITIONAL_TEMPLATE.format(alias="fact"),
        _AUTHORED_SUPERSESSION_TEMPLATE.format(
            alias="fact", successor_eligible=_SUCCESSOR_ELIGIBLE
        ),
        FACT_ENDPOINTS_IN_SCOPE,
    )
)

COMMITMENT_ELIGIBLE = """commitment.playthrough_id = %(playthrough_id)s::uuid
AND commitment.opened_seq <= %(at_seq)s::integer
AND (
    latest_status.commitment_id IS NULL
    OR latest_status.status = 'open'
    OR latest_status.at_seq
        >= %(at_seq)s::integer - %(commitment_recent_resolution_turns)s::integer
)"""

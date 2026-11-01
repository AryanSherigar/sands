"""Finds the live facts that a batch's new facts replace: deterministic rules first,
one judge call for what the rules cannot decide. Runs before the plan is stored, so
apply never calls a model."""

from dataclasses import dataclass, field
from uuid import UUID

import structlog
from app.config import Settings
from app.exceptions.extraction_exceptions import (
    ExtractionConfigError,
    ExtractionInvalidOutputError,
    ExtractionPermanentError,
    ExtractionRateLimitedError,
    ExtractionTransientError,
)
from app.integrations.extraction_client import ExtractionBackend
from app.models.extraction import ExtractedFact, SupersessionClaim, ValidatedPlan
from app.models.facts import FactRow
from app.models.jobs import ExtractionBatchRow
from app.models.templates import PlaythroughRow
from app.repositories import entity_repo, fact_repo, playthrough_repo
from app.services.extraction_input import BuiltInput, load_system_prompt
from app.services.retrieval_types import build_scopes
from app.services.supersession_rules import (
    CandidateContext,
    FactCandidates,
    render_judge_input,
    select_candidates,
    split_by_tier,
    validate_judgements,
)
from psycopg import AsyncConnection

JUDGE_PROMPT_VERSION = "supersession_v1"
MODE_OFF = "off"
MODE_RULES_AND_JUDGE = "rules_and_judge"
PLAYTHROUGH_SCOPE = "playthrough"
EVENT_JUDGE_FAILED = "supersession_judge_failed"
DROP_JUDGE_FAILED = "judge_failed"
DROP_JUDGE_PAIRS_SKIPPED = "judge_pairs_skipped"
JUDGE_FAILURES = (
    ExtractionTransientError,
    ExtractionInvalidOutputError,
    ExtractionPermanentError,
    ExtractionRateLimitedError,
    ExtractionConfigError,
)

logger = structlog.get_logger()


@dataclass(frozen=True)
class PreparedResolution:
    rule_claims: list[SupersessionClaim]
    ambiguous: list[FactCandidates]
    refs: dict[str, str]
    names: dict[str, str]
    evidence_by_index: dict[int, str]


@dataclass(frozen=True)
class Resolution:
    claims: list[SupersessionClaim] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    drops: dict[str, int] = field(default_factory=dict)


def _uuid_or_none(value: str | None) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _subject_id(fact: ExtractedFact, refs: dict[str, str]) -> UUID | None:
    return _uuid_or_none(refs.get(fact.subject, fact.subject))


def _candidate_pairs(
    plan: ValidatedPlan, ctx: CandidateContext
) -> list[FactCandidates]:
    pairs: list[FactCandidates] = []
    for index, fact in enumerate(plan.facts):
        subject = _subject_id(fact, ctx.refs)
        if fact.assertion != "occurred" or subject is None:
            continue
        candidates = select_candidates(fact, subject, ctx)
        if candidates:
            pairs.append(FactCandidates(index, fact, subject, candidates))
    return pairs


def _entities_in_play(plan: ValidatedPlan, built: BuiltInput) -> list[UUID]:
    refs = plan.reused_entities
    subjects = (
        _subject_id(fact, refs) for fact in plan.facts if fact.assertion == "occurred"
    )
    roster = (
        _uuid_or_none(entity_id) for entity_id in built.validation.roster_entity_ids
    )
    found = [item for item in [*subjects, *roster] if item is not None]
    return list(dict.fromkeys(found))


async def _entity_names(
    connection: AsyncConnection,
    playthrough: PlaythroughRow,
    plan: ValidatedPlan,
    rows: list[FactRow],
    in_play: list[UUID],
) -> dict[str, str]:
    scopes = build_scopes(playthrough.playthrough_id, playthrough.template_id)
    referenced = {row.object_entity_id for row in rows if row.object_entity_id}
    referenced.update(row.subject_entity_id for row in rows)
    referenced.update(in_play)
    entities = await entity_repo.get_entities(connection, scopes, list(referenced))
    names = {str(row.entity_id): row.canonical_name for row in entities}
    names.update({entity.temp_key: entity.name for entity in plan.new_entities})
    return names


def _evidence_texts(pairs: list[FactCandidates], built: BuiltInput) -> dict[int, str]:
    texts: dict[int, str] = {}
    for pair in pairs:
        spans = [
            built.spans_by_label[label]
            for label in pair.fact.evidence
            if label in built.spans_by_label
        ]
        texts[pair.fact_index] = " ".join(span.text for span in spans)
    return texts


async def _candidate_context(
    connection: AsyncConnection,
    batch: ExtractionBatchRow,
    playthrough: PlaythroughRow,
    built: BuiltInput,
    plan: ValidatedPlan,
    settings: Settings,
) -> CandidateContext:
    in_play = _entities_in_play(plan, built)
    rows = await fact_repo.list_valid_facts_at(
        connection,
        batch.scope_id,
        playthrough.template_id,
        batch.from_seq - 1,
        subject_entity_ids=in_play,
    )
    names = await _entity_names(connection, playthrough, plan, rows, in_play)
    return CandidateContext(
        refs=dict(plan.reused_entities),
        names=names,
        live_rows=tuple(rows),
        cap=settings.supersession_candidate_cap,
    )


async def prepare_resolution(
    connection: AsyncConnection,
    batch: ExtractionBatchRow,
    built: BuiltInput,
    plan: ValidatedPlan,
    settings: Settings,
) -> PreparedResolution | None:
    if settings.supersession_resolution_mode == MODE_OFF:
        return None
    if batch.scope_kind != PLAYTHROUGH_SCOPE:
        return None
    playthrough = await playthrough_repo.get_playthrough(connection, batch.scope_id)
    if playthrough is None or not any(f.assertion == "occurred" for f in plan.facts):
        return None
    ctx = await _candidate_context(
        connection, batch, playthrough, built, plan, settings
    )
    functional = frozenset(settings.supersession_functional_predicates)
    rule_claims, ambiguous = split_by_tier(_candidate_pairs(plan, ctx), functional)
    return PreparedResolution(
        rule_claims, ambiguous, ctx.refs, ctx.names, _evidence_texts(ambiguous, built)
    )


async def resolve_with_judge(
    client: ExtractionBackend, prepared: PreparedResolution, settings: Settings
) -> Resolution:
    """Fail-open: a judge error leaves only the rule claims, never fails the batch."""
    pairs = prepared.ambiguous[: settings.supersession_judge_max_pairs]
    skipped = len(prepared.ambiguous) - len(pairs)
    drops = {DROP_JUDGE_PAIRS_SKIPPED: skipped} if skipped else {}
    should_judge = (
        pairs and settings.supersession_resolution_mode == MODE_RULES_AND_JUDGE
    )
    if not should_judge:
        return Resolution(prepared.rule_claims, drops=drops)
    user_content = render_judge_input(
        pairs, prepared.refs, prepared.names, prepared.evidence_by_index
    )
    try:
        result = await client.judge_supersessions(
            load_system_prompt(JUDGE_PROMPT_VERSION), user_content
        )
    except JUDGE_FAILURES as error:
        logger.warning(EVENT_JUDGE_FAILED, code=error.code)
        return Resolution(prepared.rule_claims, drops={**drops, DROP_JUDGE_FAILED: 1})
    judged, judge_drops = validate_judgements(result.output, pairs)
    return Resolution(
        [*prepared.rule_claims, *judged],
        result.usage.input_tokens,
        result.usage.output_tokens,
        {**drops, **judge_drops},
    )

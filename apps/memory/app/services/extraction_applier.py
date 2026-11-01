"""Applies a validated extraction plan in the caller's transaction."""

from dataclasses import dataclass
from uuid import UUID

from app.models.evidence import SpanRow
from app.models.extraction import (
    CommitmentUpdate,
    ExtractedFact,
    NewCommitment,
    NewEntity,
    SceneClaim,
    SupersessionClaim,
    ValidatedPlan,
)
from app.models.facts import (
    AliasCreate,
    CommitmentCreate,
    CommitmentStatusCreate,
    EntityCreate,
    FactCreate,
    FactSourceCreate,
    SceneStateCreate,
    SupersessionCreate,
)
from app.models.jobs import ExtractionBatchRow
from app.repositories import (
    commitment_repo,
    entity_repo,
    fact_repo,
    scene_repo,
)
from psycopg import AsyncConnection

PLAYTHROUGH_SCOPE = "playthrough"
EXTRACTED_PROVENANCE = "extracted"
EXTRACTED_AUTHORITY = "extracted"


@dataclass(frozen=True)
class ApplyInput:
    batch: ExtractionBatchRow
    plan: ValidatedPlan
    spans_by_label: dict[str, SpanRow]

    @property
    def is_playthrough(self) -> bool:
        return self.batch.scope_kind == PLAYTHROUGH_SCOPE


def _evidence_spans(labels: list[str], spans: dict[str, SpanRow]) -> list[SpanRow]:
    return [spans[label] for label in labels if label in spans]


def _last_sequence(labels: list[str], spans: dict[str, SpanRow]) -> int:
    return max((span.sequence for span in _evidence_spans(labels, spans)), default=0)


def _first_sequence(labels: list[str], spans: dict[str, SpanRow]) -> int:
    return min((span.sequence for span in _evidence_spans(labels, spans)), default=0)


def _alias_rows(
    entity_id: UUID, entity: NewEntity, batch: ExtractionBatchRow
) -> list[AliasCreate]:
    by_normalized: dict[str, str] = {}
    for alias in [entity.name, *entity.aliases]:
        by_normalized.setdefault(entity_repo.normalize_alias(alias), alias)
    return [
        AliasCreate(
            entity_id=entity_id,
            scope_kind=batch.scope_kind,
            scope_id=batch.scope_id,
            alias=alias,
            alias_normalized=normalized,
        )
        for normalized, alias in by_normalized.items()
        if normalized
    ]


async def _create_entities(
    connection: AsyncConnection, apply_input: ApplyInput
) -> dict[str, UUID]:
    batch = apply_input.batch
    refs = {key: UUID(value) for key, value in apply_input.plan.reused_entities.items()}
    for entity in apply_input.plan.new_entities:
        row = await entity_repo.create_entity(
            connection,
            EntityCreate(
                scope_kind=batch.scope_kind,
                scope_id=batch.scope_id,
                entity_type=entity.entity_type,
                canonical_name=entity.name.strip(),
                provenance=EXTRACTED_PROVENANCE,
                first_seen_seq=_first_sequence(
                    entity.evidence, apply_input.spans_by_label
                ),
            ),
        )
        await entity_repo.add_aliases(
            connection, _alias_rows(row.entity_id, entity, batch)
        )
        refs[entity.temp_key] = row.entity_id
    return refs


def _resolve(ref: str | None, refs: dict[str, UUID]) -> UUID | None:
    if ref is None:
        return None
    return refs[ref] if ref in refs else UUID(ref)


def _fact_create(
    fact: ExtractedFact, refs: dict[str, UUID], apply_input: ApplyInput
) -> FactCreate:
    batch = apply_input.batch
    subject = _resolve(fact.subject, refs)
    assert subject is not None
    return FactCreate(
        scope_kind=batch.scope_kind,
        scope_id=batch.scope_id,
        subject_entity_id=subject,
        predicate=fact.predicate,
        object_entity_id=_resolve(fact.object, refs),
        object_literal=(fact.object_literal or "").strip() or None,
        authority=EXTRACTED_AUTHORITY,
        assertion=fact.assertion,
        speaker_entity_id=_resolve(fact.speaker, refs),
        valid_from_seq=_last_sequence(fact.evidence, apply_input.spans_by_label),
        extraction_batch_id=batch.batch_id,
    )


async def _create_facts(
    connection: AsyncConnection, apply_input: ApplyInput, refs: dict[str, UUID]
) -> int:
    facts = apply_input.plan.facts
    rows = await fact_repo.create_facts(
        connection, [_fact_create(fact, refs, apply_input) for fact in facts]
    )
    links = [
        FactSourceCreate(fact_id=row.fact_id, span_id=span.span_id)
        for fact, row in zip(facts, rows, strict=True)
        for span in _evidence_spans(fact.evidence, apply_input.spans_by_label)
    ]
    await fact_repo.add_fact_sources(connection, links)
    return len(rows)


def _supersession_create(
    claim: SupersessionClaim, apply_input: ApplyInput
) -> SupersessionCreate:
    spans = apply_input.spans_by_label
    evidence = _evidence_spans(claim.evidence, spans)
    return SupersessionCreate(
        playthrough_id=apply_input.batch.scope_id,
        fact_id=UUID(claim.fact_id),
        at_seq=_last_sequence(claim.evidence, spans),
        authority=EXTRACTED_AUTHORITY,
        evidence_span_id=evidence[0].span_id if evidence else None,
        extraction_batch_id=apply_input.batch.batch_id,
    )


async def _create_supersessions(
    connection: AsyncConnection, apply_input: ApplyInput
) -> int:
    claims = apply_input.plan.supersessions
    await fact_repo.add_supersessions(
        connection, [_supersession_create(claim, apply_input) for claim in claims]
    )
    return len(claims)


def _commitment_create(
    commitment: NewCommitment, refs: dict[str, UUID], apply_input: ApplyInput
) -> CommitmentCreate:
    spans = apply_input.spans_by_label
    owner = _resolve(commitment.owner, refs)
    assert owner is not None
    return CommitmentCreate(
        playthrough_id=apply_input.batch.scope_id,
        kind=commitment.kind,
        owner_entity_id=owner,
        counterparty_entity_id=_resolve(commitment.counterparty, refs),
        summary=commitment.summary.strip(),
        opened_seq=_first_sequence(commitment.evidence, spans),
        opening_span_id=_evidence_spans(commitment.evidence, spans)[0].span_id,
        extraction_batch_id=apply_input.batch.batch_id,
    )


async def _create_commitments(
    connection: AsyncConnection, apply_input: ApplyInput, refs: dict[str, UUID]
) -> int:
    for commitment in apply_input.plan.new_commitments:
        await commitment_repo.create_commitment(
            connection, _commitment_create(commitment, refs, apply_input)
        )
    return len(apply_input.plan.new_commitments)


def _status_create(
    update: CommitmentUpdate, apply_input: ApplyInput
) -> CommitmentStatusCreate:
    spans = apply_input.spans_by_label
    evidence = _evidence_spans(update.evidence, spans)
    return CommitmentStatusCreate(
        commitment_id=UUID(update.commitment_id),
        at_seq=_last_sequence(update.evidence, spans),
        status=update.status,
        evidence_span_id=evidence[0].span_id if evidence else None,
        extraction_batch_id=apply_input.batch.batch_id,
    )


async def _apply_commitment_updates(
    connection: AsyncConnection, apply_input: ApplyInput
) -> int:
    for update in apply_input.plan.commitment_updates:
        await commitment_repo.append_commitment_status(
            connection, _status_create(update, apply_input)
        )
    return len(apply_input.plan.commitment_updates)


async def _apply_scene(
    connection: AsyncConnection,
    scene: SceneClaim | None,
    apply_input: ApplyInput,
    refs: dict[str, UUID],
) -> int:
    if scene is None:
        return 0
    await scene_repo.append_scene_state(
        connection,
        SceneStateCreate(
            playthrough_id=apply_input.batch.scope_id,
            valid_from_seq=_last_sequence(scene.evidence, apply_input.spans_by_label),
            location_entity_id=_resolve(scene.location, refs),
            present_entity_ids=[
                entity_id
                for ref in scene.present
                if (entity_id := _resolve(ref, refs)) is not None
            ],
            extraction_batch_id=apply_input.batch.batch_id,
        ),
    )
    return 1


async def apply_plan(connection: AsyncConnection, apply_input: ApplyInput) -> int:
    """Returns the number of rows written. Commitments, supersessions and scene apply
    only to playthrough scope; a template plan carries none of them."""
    refs = await _create_entities(connection, apply_input)
    applied = len(apply_input.plan.new_entities)
    applied += await _create_facts(connection, apply_input, refs)
    if not apply_input.is_playthrough:
        return applied
    applied += await _create_supersessions(connection, apply_input)
    applied += await _create_commitments(connection, apply_input, refs)
    applied += await _apply_commitment_updates(connection, apply_input)
    applied += await _apply_scene(connection, apply_input.plan.scene, apply_input, refs)
    return applied

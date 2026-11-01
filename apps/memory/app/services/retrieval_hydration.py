"""Loads what rendering needs for the fused survivors: entity names, span origins and
the labels of eligible commitment evidence spans."""

from uuid import UUID

from app.models.eligibility import EligibilityContext
from app.models.facts import FactRow
from app.repositories import entity_repo, span_repo
from app.services.fusion import FusedCandidate
from app.services.packing import RenderContext
from app.services.retrieval_types import CandidatePool, Scope
from psycopg import AsyncConnection


def _fact_entity_ids(fact: FactRow) -> list[UUID | None]:
    return [fact.subject_entity_id, fact.object_entity_id, fact.speaker_entity_id]


def _collect_entity_ids(
    fused_candidates: list[FusedCandidate], pool: CandidatePool
) -> list[UUID]:
    found: list[UUID | None] = []
    for fused in fused_candidates:
        item_id = fused.candidate.item_id
        if fused.candidate.kind == "fact":
            found.extend(_fact_entity_ids(pool.facts[item_id]))
        if fused.candidate.kind == "commitment":
            commitment = pool.commitments[item_id].commitment
            found.extend(
                [commitment.owner_entity_id, commitment.counterparty_entity_id]
            )
    return list(dict.fromkeys(entity_id for entity_id in found if entity_id))


def _collect_evidence_span_ids(
    fused_candidates: list[FusedCandidate], pool: CandidatePool
) -> list[UUID]:
    span_ids: list[UUID] = []
    for fused in fused_candidates:
        if fused.candidate.kind != "commitment":
            continue
        status = pool.commitments[fused.candidate.item_id].status
        if status is not None and status.evidence_span_id is not None:
            span_ids.append(status.evidence_span_id)
    return list(dict.fromkeys(span_ids))


def _collect_span_ids(fused_candidates: list[FusedCandidate]) -> list[UUID]:
    return [
        fused.candidate.item_id
        for fused in fused_candidates
        if fused.candidate.kind == "span"
    ]


async def load_render_context(
    connection: AsyncConnection,
    ctx: EligibilityContext,
    scopes: list[Scope],
    fused_candidates: list[FusedCandidate],
    pool: CandidatePool,
    participant_names: dict[UUID, str],
) -> RenderContext:
    entity_ids = _collect_entity_ids(fused_candidates, pool)
    entities = await entity_repo.get_entities(connection, scopes, entity_ids)
    origins = await span_repo.get_span_origins(
        connection, ctx, _collect_span_ids(fused_candidates)
    )
    evidence_ids = _collect_evidence_span_ids(fused_candidates, pool)
    evidence = await span_repo.get_eligible_spans_by_ids(connection, ctx, evidence_ids)
    return RenderContext(
        entity_names={entity.entity_id: entity.canonical_name for entity in entities},
        participant_names=participant_names,
        span_origins=origins,
        evidence_labels={span.span_id: span.label for span in evidence},
    )

"""Assembles the retrieve response and writes its single log line."""

import structlog
from app.models.facts import EntityRow, SceneStateRow
from app.models.retrieve import (
    ActiveEntity,
    DegradedReason,
    MemoryItem,
    RetrievalBranch,
    RetrieveRequest,
    RetrieveResponse,
    SceneAtSequence,
    Watermarks,
)
from app.models.templates import PlaythroughRow
from app.services.fusion import BRANCH_ORDER
from app.services.retrieval_types import RetrievalRun

logger = structlog.get_logger()

NO_EMBEDDING_MODEL = ""


def build_active_entities(seeds: list[EntityRow]) -> list[ActiveEntity]:
    return [
        ActiveEntity(
            entity_id=seed.entity_id,
            authored_entity_id=seed.authored_entity_id,
            name=seed.canonical_name,
            provenance=seed.provenance,
            brief=None,
        )
        for seed in seeds
    ]


def build_scene(scene: SceneStateRow | None) -> SceneAtSequence | None:
    if scene is None:
        return None
    return SceneAtSequence(
        valid_from_seq=scene.valid_from_seq,
        location_entity_id=scene.location_entity_id,
        present_entity_ids=list(scene.present_entity_ids),
    )


def build_watermarks(playthrough: PlaythroughRow) -> Watermarks:
    return Watermarks(
        ingested_seq=playthrough.ingested_seq,
        indexed_seq=playthrough.indexed_seq,
        extracted_seq=playthrough.extracted_seq,
        latest_seq_seen=playthrough.latest_seq_seen,
    )


def order_skipped(skipped: list[RetrievalBranch]) -> list[RetrievalBranch]:
    return [branch for branch in BRANCH_ORDER if branch in skipped]


def assemble_response(
    *,
    items: list[MemoryItem],
    run: RetrievalRun,
    playthrough: PlaythroughRow,
    degraded_reasons: list[DegradedReason],
) -> RetrieveResponse:
    model_name = run.active_model.model if run.active_model else NO_EMBEDDING_MODEL
    return RetrieveResponse(
        items=items,
        active_entities=build_active_entities(run.seeds),
        scene=build_scene(run.scene),
        watermarks=build_watermarks(playthrough),
        degraded_reasons=degraded_reasons,
        embedding_model=model_name,
        skipped_branches=order_skipped(run.skipped),
    )


def log_retrieval(
    request: RetrieveRequest,
    run: RetrievalRun,
    response: RetrieveResponse,
    packed_tokens: int,
) -> None:
    """Ids, counts and timings only; never request or retrieved text."""
    logger.info(
        "retrieve_completed",
        playthrough_id=str(request.playthrough_id),
        at_seq=request.sequence,
        seed_count=len(run.seeds),
        branch_counts=run.branch_counts,
        packed_item_count=len(response.items),
        packed_tokens=packed_tokens,
        stage_ms=run.timer.stage_ms,
        skipped_branches=response.skipped_branches,
        degraded_reasons=response.degraded_reasons,
        action_mode=request.action_mode,
        actor_participant_id=str(request.actor_participant_id),
    )

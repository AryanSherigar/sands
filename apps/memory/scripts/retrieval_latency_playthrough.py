"""Playthrough content: real ingested turns, commitments and scene states."""

import random
from uuid import UUID

from app.models.facts import (
    CommitmentCreate,
    CommitmentRow,
    CommitmentStatusCreate,
    EntityRow,
    SceneStateCreate,
)
from app.models.ingest import (
    AcceptedDelta,
    AcceptedDeltaItem,
    IngestItem,
    IngestRequest,
    PlayerEntityPayload,
    RegisterItem,
    RegisterPayload,
    TurnItem,
    TurnPayload,
)
from app.models.jobs import ExtractionBatchCreate
from app.models.templates import TemplateRow
from app.repositories import (
    commitment_repo,
    extraction_batch_repo,
    scene_repo,
    span_repo,
)
from app.services.ingest_service import IngestService
from psycopg import AsyncConnection

from scripts import retrieval_latency_text as text
from scripts.retrieval_latency_types import BuiltCorpus, make_uuid

INGEST_BATCH_TURNS = 10
MUTATION_EVERY_TURNS = 5
MUTATION_ATTRIBUTE = "mood"
COMMITMENT_RESOLUTION_WINDOW = 20
FULFILLED_EVERY_NTH = 2
SCENE_PRESENT_COUNT = 3
TURN_ENTITY_MENTIONS = 2
BATCH_MODEL = "latency-batch"
BATCH_MARKER = "latency"


def _require_authored_id(entity: EntityRow) -> UUID:
    if entity.authored_entity_id is None:
        raise RuntimeError(f"Entity {entity.canonical_name} has no authored id.")
    return entity.authored_entity_id


def _register_item(template: TemplateRow, player: EntityRow) -> RegisterItem:
    return RegisterItem(
        item_kind="register_playthrough",
        sequence=0,
        payload=RegisterPayload(
            scenario_id=template.scenario_id,
            publish_revision=template.publish_revision,
            player_entity=PlayerEntityPayload(
                authored_entity_id=_require_authored_id(player),
                canonical_name=player.canonical_name,
                aliases=list(text.build_entity_name(0).aliases),
                entity_type=player.entity_type,
            ),
        ),
    )


def _mutation_delta(sequence: int, player: EntityRow) -> AcceptedDelta:
    if sequence % MUTATION_EVERY_TURNS != 0:
        return AcceptedDelta()
    key = f"{player.authored_entity_id}.{MUTATION_ATTRIBUTE}"
    item = AcceptedDeltaItem(kind="state_mutation", key=key, after=f"mood-{sequence}")
    return AcceptedDelta(items=[item])


def _turn_item(
    rng: random.Random, sequence: int, entities: list[EntityRow]
) -> TurnItem:
    mentioned = rng.sample(entities, TURN_ENTITY_MENTIONS)
    names = [each.canonical_name for each in mentioned]
    return TurnItem(
        item_kind="turn",
        sequence=sequence,
        payload=TurnPayload(
            turn_id=make_uuid(rng),
            turn_number=sequence,
            participant_id=make_uuid(rng),
            action_mode="do",
            action_text=text.turn_action(rng, names[0]),
            narration_text=text.lore_paragraph(rng, names),
            accepted_delta=_mutation_delta(sequence, entities[0]),
        ),
    )


async def register_and_ingest(
    connection: AsyncConnection,
    rng: random.Random,
    corpus: BuiltCorpus,
    template: TemplateRow,
    entities: list[EntityRow],
) -> None:
    service = IngestService(connection)
    turns = [
        _turn_item(rng, sequence, entities)
        for sequence in range(1, corpus.spec.turn_count + 1)
    ]
    items: list[IngestItem] = [_register_item(template, entities[0])]
    for start in range(0, len(turns), INGEST_BATCH_TURNS):
        items.extend(turns[start : start + INGEST_BATCH_TURNS])
        request = IngestRequest(playthrough_id=corpus.playthrough_id, items=items)
        await service.ingest_items(request)
        items = []
    await connection.commit()


async def _create_batch(connection: AsyncConnection, corpus: BuiltCorpus) -> UUID:
    batch = await extraction_batch_repo.create_batch(
        connection,
        ExtractionBatchCreate(
            scope_kind="playthrough",
            scope_id=corpus.playthrough_id,
            from_seq=1,
            to_seq=corpus.spec.turn_count,
            status="applied",
            model=BATCH_MODEL,
            prompt_version=BATCH_MARKER,
            input_hash=BATCH_MARKER,
        ),
    )
    return batch.batch_id


async def _add_commitment(
    connection: AsyncConnection,
    rng: random.Random,
    corpus: BuiltCorpus,
    entities: list[EntityRow],
    span_ids: list[UUID],
    batch_id: UUID,
) -> CommitmentRow:
    opened_seq = rng.randint(1, corpus.spec.turn_count)
    return await commitment_repo.create_commitment(
        connection,
        CommitmentCreate(
            playthrough_id=corpus.playthrough_id,
            kind="promise",
            owner_entity_id=rng.choice(entities).entity_id,
            counterparty_entity_id=rng.choice(entities).entity_id,
            summary=f"a promise about the {rng.choice(text.LORE_VOCABULARY)}",
            opened_seq=opened_seq,
            opening_span_id=rng.choice(span_ids),
            extraction_batch_id=batch_id,
        ),
    )


async def _fulfil_commitment(
    connection: AsyncConnection,
    rng: random.Random,
    corpus: BuiltCorpus,
    commitment: CommitmentRow,
) -> None:
    delay = rng.randint(1, COMMITMENT_RESOLUTION_WINDOW)
    resolved_at = min(corpus.spec.turn_count, commitment.opened_seq + delay)
    await commitment_repo.append_commitment_status(
        connection,
        CommitmentStatusCreate(
            commitment_id=commitment.commitment_id,
            at_seq=resolved_at,
            status="fulfilled",
        ),
    )


async def _add_scenes(
    connection: AsyncConnection,
    rng: random.Random,
    corpus: BuiltCorpus,
    entities: list[EntityRow],
    batch_id: UUID,
) -> None:
    step = corpus.spec.scene_every_turns
    if step <= 0:
        return
    for valid_from in range(1, corpus.spec.turn_count + 1, step):
        present = rng.sample(entities, SCENE_PRESENT_COUNT)
        await scene_repo.append_scene_state(
            connection,
            SceneStateCreate(
                playthrough_id=corpus.playthrough_id,
                valid_from_seq=valid_from,
                location_entity_id=rng.choice(entities).entity_id,
                present_entity_ids=[each.entity_id for each in present],
                extraction_batch_id=batch_id,
            ),
        )


async def add_commitments_and_scenes(
    connection: AsyncConnection,
    rng: random.Random,
    corpus: BuiltCorpus,
    entities: list[EntityRow],
) -> None:
    batch_id = await _create_batch(connection, corpus)
    spans = await span_repo.list_spans_by_sequence(
        connection, "playthrough", corpus.playthrough_id, 1, corpus.spec.turn_count
    )
    span_ids = [span.span_id for span in spans]
    for index in range(corpus.spec.commitment_count):
        commitment = await _add_commitment(
            connection, rng, corpus, entities, span_ids, batch_id
        )
        if index % FULFILLED_EVERY_NTH == 0:
            await _fulfil_commitment(connection, rng, corpus, commitment)
    await _add_scenes(connection, rng, corpus, entities, batch_id)
    await connection.commit()

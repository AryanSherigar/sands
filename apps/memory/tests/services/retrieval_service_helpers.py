"""Corpus builders, a scripted query embedder and request builders for the retrieval
service tests. Everything is written through the app's own repositories."""

import asyncio
from uuid import UUID, uuid4

from app.config import Settings
from app.models.common import ExtractionBatchStatus, ScopeKind
from app.models.evidence import SourceCreate, SpanCreate, SpanRow
from app.models.facts import (
    AliasCreate,
    EntityCreate,
    EntityRow,
    FactRow,
    SceneStateCreate,
)
from app.models.jobs import ExtractionBatchCreate
from app.models.retrieve import RetrieveRequest
from app.repositories import (
    embedding_repo,
    entity_repo,
    extraction_batch_repo,
    scene_repo,
    source_repo,
    span_repo,
)
from app.services.fact_text import render_fact_text
from app.services.retrieval_service import QueryEmbedder, RetrievalService
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.repositories import helpers_retrieval as helpers
from tests.repositories.helpers_retrieval import Scope, World
from tests.services.indexing_helpers import TEST_DIM, vector_for

MODEL = ("model-a", "1")
DEFAULT_SEQUENCE = 30
BASE_SETTINGS = {
    "embedding_api_key": "test-key",
    "embedding_model_name": MODEL[0],
    "embedding_model_version": MODEL[1],
    "embedding_dim": TEST_DIM,
}


def make_settings(**overrides: int | float | str) -> Settings:
    values: dict[str, int | float | str] = dict(BASE_SETTINGS)
    values.update(overrides)
    return Settings(**values)


class FakeQueryEmbedder:
    """Deterministic hash-vector query embedder. `events` may be shared with other
    spies to assert call ordering; failures and delays are scripted."""

    def __init__(self, events: list[str] | None = None) -> None:
        self.events = events if events is not None else []
        self.texts: list[str] = []
        self.error: Exception | None = None
        self.delay_seconds = 0.0
        self.was_cancelled = False

    async def __call__(self, text: str) -> list[float]:
        self.events.append("embed_started")
        self.texts.append(text)
        try:
            await asyncio.sleep(self.delay_seconds)
        except asyncio.CancelledError:
            self.was_cancelled = True
            raise
        if self.error is not None:
            raise self.error
        return vector_for(text)


async def add_entity(
    connection: AsyncConnection,
    scope: Scope,
    name: str,
    *,
    aliases: tuple[str, ...] = (),
    authored_id: UUID | None = None,
    is_player: bool = False,
) -> EntityRow:
    """Registers the canonical name (normalized) and every extra alias."""
    entity = await entity_repo.create_entity(
        connection,
        EntityCreate(
            scope_kind=scope[0],
            scope_id=scope[1],
            authored_entity_id=authored_id,
            entity_type="character",
            canonical_name=name,
            provenance="authored" if authored_id else "extracted",
            first_seen_seq=0,
            is_player=is_player,
        ),
    )
    alias_rows = [
        AliasCreate(
            entity_id=entity.entity_id,
            scope_kind=scope[0],
            scope_id=scope[1],
            alias=alias,
            alias_normalized=entity_repo.normalize_alias(alias),
        )
        for alias in (name, *aliases)
    ]
    await entity_repo.add_aliases(connection, alias_rows)
    return entity


async def add_batch(
    connection: AsyncConnection,
    playthrough_id: UUID,
    status: ExtractionBatchStatus = "applied",
) -> UUID:
    batch = await extraction_batch_repo.create_batch(
        connection,
        ExtractionBatchCreate(
            scope_kind="playthrough",
            scope_id=playthrough_id,
            from_seq=1,
            to_seq=2,
            status=status,
            model="test-model",
            prompt_version=str(uuid4()),
            input_hash=str(uuid4()),
        ),
    )
    return batch.batch_id


async def add_scene(
    connection: AsyncConnection,
    playthrough_id: UUID,
    valid_from_seq: int,
    *,
    location: UUID | None,
    present: list[UUID],
) -> None:
    batch_id = await add_batch(connection, playthrough_id)
    await scene_repo.append_scene_state(
        connection,
        SceneStateCreate(
            playthrough_id=playthrough_id,
            valid_from_seq=valid_from_seq,
            location_entity_id=location,
            present_entity_ids=present,
            extraction_batch_id=batch_id,
        ),
    )


async def activate_model(
    connection: AsyncConnection, model: tuple[str, str] = MODEL
) -> None:
    await helpers.register_model(connection, model, TEST_DIM)
    await embedding_repo.activate_embedding_model(connection, *model)


async def add_span(
    connection: AsyncConnection,
    scope: Scope,
    text: str,
    *,
    sequence: int = 1,
    entity_ids: list[UUID] | None = None,
    is_embedded: bool = True,
    **options: object,
) -> SpanRow:
    span = await helpers.add_span(
        connection,
        scope,
        text=text,
        sequence=sequence,
        entity_ids=entity_ids,
        **options,  # type: ignore[arg-type]
    )
    if is_embedded:
        await helpers.add_embedding(
            connection, "span", span.span_id, scope, vector_for(text), MODEL
        )
    return span


async def add_fact(
    connection: AsyncConnection,
    scope: Scope,
    subject: EntityRow,
    predicate: str,
    *,
    object_entity: EntityRow | None = None,
    object_literal: str | None = None,
    is_embedded: bool = False,
    **options: object,
) -> FactRow:
    fact = await helpers.add_fact(
        connection,
        scope,
        subject.entity_id,
        predicate,
        object_entity_id=object_entity.entity_id if object_entity else None,
        object_literal=object_literal,
        **options,  # type: ignore[arg-type]
    )
    if is_embedded:
        object_text = object_entity.canonical_name if object_entity else object_literal
        text = render_fact_text(subject.canonical_name, predicate, object_text or "")
        await helpers.add_embedding(
            connection, "fact", fact.fact_id, scope, vector_for(text), MODEL
        )
    return fact


def make_request(
    world: World,
    action_text: str,
    *,
    sequence: int = DEFAULT_SEQUENCE,
    **overrides: object,
) -> RetrieveRequest:
    values: dict[str, object] = {
        "playthrough_id": world.playthrough_id,
        "sequence": sequence,
        "action_text": action_text,
        "action_mode": "do",
        "actor_participant_id": uuid4(),
        "recent_text": "",
    }
    values.update(overrides)
    return RetrieveRequest(**values)  # type: ignore[arg-type]


def texts_of(response_items: list) -> list[str]:
    return [each.text for each in response_items]


def scope_of(world: World, name: str) -> Scope:
    scopes: dict[str, tuple[ScopeKind, UUID]] = {
        "template": world.template_scope,
        "playthrough": world.playthrough_scope,
        "sibling": world.sibling_scope,
        "foreign": world.foreign_scope,
    }
    return scopes[name]


def build_service(
    pool: AsyncConnectionPool,
    embedder: QueryEmbedder | None,
    **settings_overrides: int | float | str,
) -> RetrievalService:
    return RetrievalService(pool, make_settings(**settings_overrides), embedder)


async def add_actor_span(
    connection: AsyncConnection,
    scope: Scope,
    text: str,
    sequence: int,
    actor_participant_id: UUID,
    entity_ids: list[UUID],
) -> SpanRow:
    """A turn span whose source records who acted."""
    source = await source_repo.create_source(
        connection,
        SourceCreate(
            scope_kind=scope[0],
            scope_id=scope[1],
            source_kind="turn_action",
            source_ref=str(uuid4()),
            sequence=sequence,
            actor_participant_id=actor_participant_id,
            content=text,
            content_hash="hash",
        ),
    )
    spans = await span_repo.create_spans(
        connection,
        [
            SpanCreate(
                source_id=source.source_id,
                scope_kind=scope[0],
                scope_id=scope[1],
                sequence=sequence,
                ordinal=0,
                start_offset=0,
                end_offset=len(text),
                text=text,
                token_count=1,
                label=f"S{sequence}",
                entity_ids=entity_ids,
            )
        ],
    )
    return spans[0]

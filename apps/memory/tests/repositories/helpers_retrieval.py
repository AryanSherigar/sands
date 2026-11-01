"""Fixture builders for retrieval tests: scoped worlds, spans, facts, commitments and
embeddings, written through the app's own repositories."""

from dataclasses import dataclass
from uuid import UUID, uuid4

from app.models.common import (
    CommitmentKind,
    CommitmentStatusValue,
    EmbeddingTargetKind,
    ScopeKind,
    SourceKind,
)
from app.models.eligibility import EligibilityContext
from app.models.evidence import SourceCreate, SpanCreate, SpanRow
from app.models.facts import (
    CommitmentCreate,
    CommitmentRow,
    CommitmentStatusCreate,
    EntityCreate,
    FactCreate,
    FactRow,
    FactSourceCreate,
    SupersessionCreate,
)
from app.models.jobs import EmbeddingCreate, EmbeddingModelCreate, ExtractionBatchCreate
from app.repositories import (
    commitment_repo,
    embedding_repo,
    entity_repo,
    extraction_batch_repo,
    fact_repo,
    source_repo,
    span_repo,
)
from psycopg import AsyncConnection
from tests.repositories.helpers_evidence import make_playthrough, make_template

Scope = tuple[ScopeKind, UUID]

DEFAULT_AT_SEQ = 30
DEFAULT_WINDOW = 6
DEFAULT_MODEL = ("model-a", "v1")
DEFAULT_DIM = 3


@dataclass(frozen=True)
class World:
    """Two playthroughs of one template, plus a playthrough of another template."""

    template_id: UUID
    playthrough_id: UUID
    sibling_playthrough_id: UUID
    other_template_id: UUID
    foreign_playthrough_id: UUID

    @property
    def template_scope(self) -> Scope:
        return ("template", self.template_id)

    @property
    def playthrough_scope(self) -> Scope:
        return ("playthrough", self.playthrough_id)

    @property
    def sibling_scope(self) -> Scope:
        return ("playthrough", self.sibling_playthrough_id)

    @property
    def foreign_scope(self) -> Scope:
        return ("playthrough", self.foreign_playthrough_id)

    @property
    def other_template_scope(self) -> Scope:
        return ("template", self.other_template_id)


async def build_world(connection: AsyncConnection) -> World:
    template = await make_template(connection, publish_revision=1)
    other_template = await make_template(connection, publish_revision=2)
    playthrough = await make_playthrough(connection, template_id=template.template_id)
    sibling = await make_playthrough(connection, template_id=template.template_id)
    foreign = await make_playthrough(connection, template_id=other_template.template_id)
    return World(
        template_id=template.template_id,
        playthrough_id=playthrough.playthrough_id,
        sibling_playthrough_id=sibling.playthrough_id,
        other_template_id=other_template.template_id,
        foreign_playthrough_id=foreign.playthrough_id,
    )


def make_context(
    world: World,
    *,
    at_seq: int = DEFAULT_AT_SEQ,
    window: int = DEFAULT_WINDOW,
    revealed: list[UUID] | None = None,
    active: list[UUID] | None = None,
    should_include_hidden: bool = False,
    has_template: bool = True,
) -> EligibilityContext:
    return EligibilityContext(
        playthrough_id=world.playthrough_id,
        template_id=world.template_id if has_template else None,
        at_seq=at_seq,
        recent_window_turns=window,
        revealed_authored_fact_ids=revealed or [],
        active_conditional_authored_fact_ids=active or [],
        should_include_hidden=should_include_hidden,
    )


async def add_entity(
    connection: AsyncConnection,
    scope: Scope,
    name: str,
    *,
    is_player: bool = False,
) -> UUID:
    entity = await entity_repo.create_entity(
        connection,
        EntityCreate(
            scope_kind=scope[0],
            scope_id=scope[1],
            entity_type="character",
            canonical_name=name,
            provenance="extracted",
            first_seen_seq=0,
            is_player=is_player,
        ),
    )
    return entity.entity_id


async def add_span(
    connection: AsyncConnection,
    scope: Scope,
    *,
    text: str,
    sequence: int = 1,
    source_kind: SourceKind = "turn_narration",
    is_hidden: bool = False,
    authored_fact_id: UUID | None = None,
    conditional: bool = False,
    entity_ids: list[UUID] | None = None,
) -> SpanRow:
    source = await source_repo.create_source(
        connection,
        SourceCreate(
            scope_kind=scope[0],
            scope_id=scope[1],
            source_kind=source_kind,
            source_ref=str(uuid4()),
            sequence=sequence,
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
                token_count=len(text.split()) or 1,
                label=f"S{sequence}",
                entity_ids=entity_ids or [],
                is_hidden=is_hidden,
                authored_fact_id=authored_fact_id,
                conditional=conditional,
            )
        ],
    )
    return spans[0]


async def add_fact(
    connection: AsyncConnection,
    scope: Scope,
    subject_entity_id: UUID,
    predicate: str,
    *,
    object_entity_id: UUID | None = None,
    object_literal: str | None = None,
    valid_from_seq: int = 0,
    is_hidden: bool = False,
    conditional: bool = False,
    authored_fact_id: UUID | None = None,
    supersedes_authored_fact_id: UUID | None = None,
) -> FactRow:
    facts = await fact_repo.create_facts(
        connection,
        [
            FactCreate(
                scope_kind=scope[0],
                scope_id=scope[1],
                subject_entity_id=subject_entity_id,
                predicate=predicate,
                object_entity_id=object_entity_id,
                object_literal=object_literal,
                authority="authored" if scope[0] == "template" else "extracted",
                assertion="occurred",
                valid_from_seq=valid_from_seq,
                authored_fact_id=authored_fact_id,
                is_hidden=is_hidden,
                conditional=conditional,
                supersedes_authored_fact_id=supersedes_authored_fact_id,
            )
        ],
    )
    return facts[0]


async def supersede_fact(
    connection: AsyncConnection, playthrough_id: UUID, fact_id: UUID, at_seq: int
) -> None:
    await fact_repo.add_supersessions(
        connection,
        [
            SupersessionCreate(
                playthrough_id=playthrough_id,
                fact_id=fact_id,
                at_seq=at_seq,
                authority="extracted",
            )
        ],
    )


async def link_fact_source(
    connection: AsyncConnection, fact_id: UUID, span_id: UUID
) -> None:
    await fact_repo.add_fact_sources(
        connection, [FactSourceCreate(fact_id=fact_id, span_id=span_id)]
    )


async def add_commitment(
    connection: AsyncConnection,
    playthrough_id: UUID,
    owner_entity_id: UUID,
    *,
    opened_seq: int,
    counterparty_entity_id: UUID | None = None,
    summary: str = "a promise",
    kind: CommitmentKind = "promise",
) -> CommitmentRow:
    opening_span = await add_span(
        connection,
        ("playthrough", playthrough_id),
        text="opening span",
        sequence=opened_seq,
    )
    batch = await extraction_batch_repo.create_batch(
        connection,
        ExtractionBatchCreate(
            scope_kind="playthrough",
            scope_id=playthrough_id,
            from_seq=1,
            to_seq=2,
            status="pending",
            model="test-model",
            prompt_version=str(uuid4()),
            input_hash=str(uuid4()),
        ),
    )
    return await commitment_repo.create_commitment(
        connection,
        CommitmentCreate(
            playthrough_id=playthrough_id,
            kind=kind,
            owner_entity_id=owner_entity_id,
            counterparty_entity_id=counterparty_entity_id,
            summary=summary,
            opened_seq=opened_seq,
            opening_span_id=opening_span.span_id,
            extraction_batch_id=batch.batch_id,
        ),
    )


async def add_commitment_status(
    connection: AsyncConnection,
    commitment_id: UUID,
    at_seq: int,
    status: CommitmentStatusValue,
) -> None:
    await commitment_repo.append_commitment_status(
        connection,
        CommitmentStatusCreate(
            commitment_id=commitment_id, at_seq=at_seq, status=status
        ),
    )


async def register_model(
    connection: AsyncConnection,
    model: tuple[str, str] = DEFAULT_MODEL,
    dim: int = DEFAULT_DIM,
) -> None:
    await embedding_repo.register_embedding_model(
        connection,
        EmbeddingModelCreate(
            model=model[0], model_version=model[1], dim=dim, is_active=False
        ),
    )


async def add_embedding(
    connection: AsyncConnection,
    target_kind: EmbeddingTargetKind,
    target_id: UUID,
    scope: Scope,
    vector: list[float],
    model: tuple[str, str] = DEFAULT_MODEL,
) -> None:
    await embedding_repo.insert_embeddings(
        connection,
        [
            EmbeddingCreate(
                target_kind=target_kind,
                target_id=target_id,
                scope_kind=scope[0],
                scope_id=scope[1],
                model=model[0],
                model_version=model[1],
                dim=len(vector),
                embedding=vector,
                content_hash="hash",
            )
        ],
    )

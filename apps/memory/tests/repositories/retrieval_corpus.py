"""One corpus, every retrieval surface: rules are asserted against each branch that
can return a span or a fact, so a predicate missing from one query shows up as a leak.

Every span carries the entity ids of all five scopes and the same embedding, and every
surface is queried with the entity ids of all five scopes, so only eligibility (never
matching) decides what comes back.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from uuid import UUID

from app.models.common import SourceKind
from app.models.eligibility import EligibilityContext
from app.repositories import embedding_repo, fact_repo, span_repo
from psycopg import AsyncConnection
from tests.repositories import helpers_retrieval as helpers
from tests.repositories.helpers_retrieval import Scope, World

PROBE_VECTOR = [1.0, 0.0, 0.0]
PROBE_WORD = "probe"
SURFACE_LIMIT = 200
HUB_EDGE_CAP = 20


@dataclass
class Corpus:
    world: World
    probe_ids: dict[Scope, UUID]
    target_ids: dict[Scope, UUID]
    span_labels: dict[UUID, str] = field(default_factory=dict)
    fact_labels: dict[UUID, str] = field(default_factory=dict)

    @property
    def all_probe_ids(self) -> list[UUID]:
        return list(self.probe_ids.values())


async def build_corpus(connection: AsyncConnection) -> Corpus:
    world = await helpers.build_world(connection)
    await helpers.register_model(connection)
    scopes = [
        world.template_scope,
        world.playthrough_scope,
        world.sibling_scope,
        world.foreign_scope,
        world.other_template_scope,
    ]
    probes = {
        scope: await helpers.add_entity(connection, scope, "Probe") for scope in scopes
    }
    targets = {
        scope: await helpers.add_entity(connection, scope, "Target") for scope in scopes
    }
    return Corpus(world=world, probe_ids=probes, target_ids=targets)


async def put_span(
    connection: AsyncConnection,
    corpus: Corpus,
    scope: Scope,
    label: str,
    *,
    sequence: int = 1,
    source_kind: SourceKind = "turn_narration",
    is_hidden: bool = False,
    conditional: bool = False,
    authored_fact_id: UUID | None = None,
    is_embedded: bool = True,
) -> UUID:
    span = await helpers.add_span(
        connection,
        scope,
        text=f"{PROBE_WORD} {label}",
        sequence=sequence,
        source_kind=source_kind,
        is_hidden=is_hidden,
        conditional=conditional,
        authored_fact_id=authored_fact_id,
        entity_ids=corpus.all_probe_ids,
    )
    corpus.span_labels[span.span_id] = label
    if is_embedded:
        await helpers.add_embedding(
            connection, "span", span.span_id, scope, PROBE_VECTOR
        )
    return span.span_id


async def put_fact(
    connection: AsyncConnection,
    corpus: Corpus,
    scope: Scope,
    label: str,
    *,
    valid_from_seq: int = 0,
    is_hidden: bool = False,
    conditional: bool = False,
    authored_fact_id: UUID | None = None,
    supersedes_authored_fact_id: UUID | None = None,
) -> UUID:
    fact = await helpers.add_fact(
        connection,
        scope,
        corpus.probe_ids[scope],
        label,
        object_entity_id=corpus.target_ids[scope],
        valid_from_seq=valid_from_seq,
        is_hidden=is_hidden,
        conditional=conditional,
        authored_fact_id=authored_fact_id,
        supersedes_authored_fact_id=supersedes_authored_fact_id,
    )
    corpus.fact_labels[fact.fact_id] = label
    await helpers.add_embedding(connection, "fact", fact.fact_id, scope, PROBE_VECTOR)
    return fact.fact_id


LabelSurface = Callable[
    [AsyncConnection, Corpus, EligibilityContext], Awaitable[set[str]]
]


async def span_labels_via_exact(
    connection: AsyncConnection, corpus: Corpus, ctx: EligibilityContext
) -> set[str]:
    rows = await span_repo.list_exact_spans(
        connection, ctx, corpus.all_probe_ids, SURFACE_LIMIT
    )
    return {corpus.span_labels[row.span_id] for row in rows}


async def span_labels_via_bm25(
    connection: AsyncConnection, corpus: Corpus, ctx: EligibilityContext
) -> set[str]:
    hits = await span_repo.search_eligible_spans_bm25(
        connection, ctx, PROBE_WORD, SURFACE_LIMIT
    )
    return {corpus.span_labels[row.span_id] for row, _score in hits}


async def _vector_hits(
    connection: AsyncConnection, ctx: EligibilityContext
) -> list[tuple[str, UUID]]:
    hits = await embedding_repo.search_eligible_embeddings(
        connection,
        ctx,
        *helpers.DEFAULT_MODEL,
        PROBE_VECTOR,
        SURFACE_LIMIT,
    )
    return [(hit.target_kind, hit.target_id) for hit in hits]


async def span_labels_via_vector(
    connection: AsyncConnection, corpus: Corpus, ctx: EligibilityContext
) -> set[str]:
    hits = await _vector_hits(connection, ctx)
    return {corpus.span_labels[uid] for kind, uid in hits if kind == "span"}


async def fact_labels_via_exact(
    connection: AsyncConnection, corpus: Corpus, ctx: EligibilityContext
) -> set[str]:
    rows = await fact_repo.list_eligible_facts_for_entities(
        connection, ctx, corpus.all_probe_ids, SURFACE_LIMIT
    )
    return {corpus.fact_labels[row.fact_id] for row in rows}


async def fact_labels_via_graph(
    connection: AsyncConnection, corpus: Corpus, ctx: EligibilityContext
) -> set[str]:
    result = await fact_repo.list_graph_edges(
        connection,
        ctx,
        corpus.all_probe_ids,
        hub_edge_cap=HUB_EDGE_CAP,
        player_entity_id=None,
    )
    return {corpus.fact_labels[row.fact_id] for row in result.edges}


async def fact_labels_via_vector(
    connection: AsyncConnection, corpus: Corpus, ctx: EligibilityContext
) -> set[str]:
    hits = await _vector_hits(connection, ctx)
    return {corpus.fact_labels[uid] for kind, uid in hits if kind == "fact"}


SPAN_SURFACES: list[LabelSurface] = [
    span_labels_via_exact,
    span_labels_via_bm25,
    span_labels_via_vector,
]
FACT_SURFACES: list[LabelSurface] = [
    fact_labels_via_exact,
    fact_labels_via_graph,
    fact_labels_via_vector,
]

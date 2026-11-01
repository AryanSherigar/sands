"""Result shapes of the retrieval repository queries."""

from uuid import UUID

from app.models.common import EmbeddingTargetKind, SourceKind
from app.models.facts import FactRow
from pydantic import BaseModel, ConfigDict


class VectorHit(BaseModel):
    model_config = ConfigDict(frozen=True)

    target_kind: EmbeddingTargetKind
    target_id: UUID
    distance: float


class GraphEdges(BaseModel):
    """`hub_entity_ids` is a subset of the queried frontier: entities with more than
    `hub_edge_cap` eligible edges, plus the player entity. Edges are ordered most
    recent first."""

    model_config = ConfigDict(frozen=True)

    edges: list[FactRow]
    hub_entity_ids: frozenset[UUID]


class SpanOrigin(BaseModel):
    """The source facts about an eligible span that rendering needs."""

    model_config = ConfigDict(frozen=True)

    source_kind: SourceKind
    actor_participant_id: UUID | None

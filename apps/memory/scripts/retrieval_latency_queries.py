"""Varied, seeded retrieval requests drawn from what a corpus really contains."""

import random
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from app.models.common import ScopeKind
from app.models.retrieve import RetrieveRequest
from app.repositories import entity_repo
from psycopg import AsyncConnection

from scripts import retrieval_latency_text as text
from scripts.retrieval_latency_types import BuiltCorpus, make_uuid

ActionMode = Literal["say", "do", "story", "see"]
QUERY_KINDS = ["entity", "lore", "pronoun", "no_entity_text"]
QUERY_KIND_WEIGHTS = [40, 20, 20, 20]
ACTION_MODES: list[ActionMode] = ["say", "do", "story", "see"]
REVEAL_SHARE = 0.25
INTERLOCUTOR_SHARE = 0.2
REVEAL_SAMPLE_SIZE = 5
LORE_QUERY_WORDS = 3
RECENT_NAME_COUNT = 2
NO_ENTITY_OPENINGS = [
    "I wait and listen for",
    "I keep walking toward the",
    "I think about",
]


@dataclass(frozen=True)
class QueryPools:
    aliases: list[str]
    authored_ids: list[UUID]


@dataclass
class RevealOptions:
    revealed_ids: list[UUID] = field(default_factory=list)
    active_ids: list[UUID] = field(default_factory=list)
    interlocutor_id: UUID | None = None


async def load_query_pools(
    connection: AsyncConnection, corpus: BuiltCorpus
) -> QueryPools:
    scopes: list[tuple[ScopeKind, UUID]] = [("template", corpus.template_id)]
    aliases = await entity_repo.list_aliases_in_scopes(connection, scopes)
    entities = await entity_repo.get_entities(connection, scopes)
    return QueryPools(
        aliases=sorted({alias for alias, _ in aliases}),
        authored_ids=[
            entity.authored_entity_id
            for entity in entities
            if entity.authored_entity_id is not None
        ],
    )


def _compose_entity(rng: random.Random, pools: QueryPools, word: str) -> str:
    opening = rng.choice(text.ACTION_OPENINGS)
    return f"{opening} {rng.choice(pools.aliases)} about the {word}"


def _compose_pronoun(
    rng: random.Random, pools: QueryPools, word: str
) -> tuple[str, str]:
    names = rng.sample(pools.aliases, RECENT_NAME_COUNT)
    recent = f"{names[0]} spoke quietly while {names[1]} watched the {word}."
    return rng.choice(text.PRONOUN_ACTIONS), recent


def compose_texts(rng: random.Random, kind: str, pools: QueryPools) -> tuple[str, str]:
    words = rng.sample(text.LORE_VOCABULARY, LORE_QUERY_WORDS)
    if kind == "entity":
        return _compose_entity(rng, pools, words[0]), ""
    if kind == "lore":
        return f"what do I know about the {' and the '.join(words)}", ""
    if kind == "pronoun":
        return _compose_pronoun(rng, pools, words[0])
    opening = rng.choice(NO_ENTITY_OPENINGS)
    return f"{opening} {words[0]}", f"The {words[1]} was quiet."


def _sample(rng: random.Random, ids: list[UUID]) -> list[UUID]:
    return rng.sample(ids, min(REVEAL_SAMPLE_SIZE, len(ids)))


def draw_reveal_options(
    rng: random.Random, corpus: BuiltCorpus, pools: QueryPools, kind: str
) -> RevealOptions:
    options = RevealOptions()
    if rng.random() < REVEAL_SHARE:
        options.revealed_ids = _sample(rng, corpus.revealable_ids)
        options.active_ids = _sample(rng, corpus.conditional_ids)
    if kind == "entity" and rng.random() < INTERLOCUTOR_SHARE:
        options.interlocutor_id = rng.choice(pools.authored_ids)
    return options


def build_request(
    rng: random.Random, corpus: BuiltCorpus, pools: QueryPools, sequence: int
) -> tuple[str, RetrieveRequest]:
    kind = rng.choices(QUERY_KINDS, weights=QUERY_KIND_WEIGHTS)[0]
    action_text, recent_text = compose_texts(rng, kind, pools)
    reveal = draw_reveal_options(rng, corpus, pools, kind)
    request = RetrieveRequest(
        playthrough_id=corpus.playthrough_id,
        sequence=sequence,
        action_text=action_text,
        action_mode=rng.choice(ACTION_MODES),
        actor_participant_id=make_uuid(rng),
        recent_text=recent_text,
        revealed_fact_ids=reveal.revealed_ids,
        active_conditional_fact_ids=reveal.active_ids,
        interlocutor_authored_entity_id=reveal.interlocutor_id,
    )
    return kind, request

"""Chooses the entities a retrieval is anchored on. The matcher is pure; the resolver
reads aliases, authored entities and the scene."""

import re
from dataclasses import dataclass
from functools import cache
from uuid import UUID

from app.models.facts import EntityRow, SceneStateRow
from app.repositories import entity_repo
from app.services.entity_tagger import build_alias_index, normalize_text_for_matching
from app.services.retrieval_types import Scope, build_scopes
from psycopg import AsyncConnection


@dataclass(frozen=True)
class SeedRequest:
    playthrough_id: UUID
    template_id: UUID | None
    action_text: str
    recent_text: str
    scene_authored_entity_ids: list[UUID]
    interlocutor_authored_entity_id: UUID | None
    scene: SceneStateRow | None
    seed_cap: int
    ambiguous_alias_seed_cap: int


@cache
def _whole_word_pattern(alias: str) -> re.Pattern[str]:
    return re.compile(rf"(?<!\w){re.escape(alias)}(?!\w)")


def _find_whole_word(alias: str, normalized_text: str) -> int | None:
    if not alias or alias not in normalized_text:
        return None
    match = _whole_word_pattern(alias).search(normalized_text)
    return match.start() if match else None


def match_aliases(
    text: str, alias_index: dict[str, set[UUID]], per_alias_cap: int
) -> list[UUID]:
    """Entity ids whose alias occurs as a whole word in `text`, earliest occurrence
    first. An ambiguous alias yields every entity it names, the first
    `per_alias_cap` by id, so the choice is deterministic."""
    normalized_text = normalize_text_for_matching(text)
    hits: list[tuple[int, str, list[UUID]]] = []
    for alias, entity_ids in alias_index.items():
        position = _find_whole_word(alias, normalized_text)
        if position is not None:
            hits.append((position, alias, sorted(entity_ids, key=str)[:per_alias_cap]))
    hits.sort(key=lambda hit: (hit[0], hit[1]))
    return list(dict.fromkeys(entity_id for _, _, ids in hits for entity_id in ids))


def order_seed_ids(
    *,
    action_ids: list[UUID],
    interlocutor_ids: list[UUID],
    scene_ids: list[UUID],
    recent_ids: list[UUID],
) -> list[UUID]:
    """Priority: action-text matches, interlocutor, scene, recent-text matches."""
    prioritized = [*action_ids, *interlocutor_ids, *scene_ids, *recent_ids]
    return list(dict.fromkeys(prioritized))


def _scene_state_ids(scene: SceneStateRow | None) -> list[UUID]:
    if scene is None:
        return []
    location = [scene.location_entity_id] if scene.location_entity_id else []
    return [*location, *scene.present_entity_ids]


def _ids_for_authored(
    rows: list[EntityRow], authored_entity_ids: list[UUID]
) -> list[UUID]:
    by_authored: dict[UUID, list[UUID]] = {}
    for row in rows:
        if row.authored_entity_id is not None:
            by_authored.setdefault(row.authored_entity_id, []).append(row.entity_id)
    ordered: list[UUID] = []
    for authored_id in authored_entity_ids:
        ordered.extend(sorted(by_authored.get(authored_id, []), key=str))
    return ordered


async def _collect_seed_ids(
    connection: AsyncConnection, request: SeedRequest, scopes: list[Scope]
) -> list[UUID]:
    alias_index = build_alias_index(
        await entity_repo.list_aliases_in_scopes(connection, scopes)
    )
    interlocutor = request.interlocutor_authored_entity_id
    interlocutor_authored_ids = [interlocutor] if interlocutor is not None else []
    authored_rows = await entity_repo.get_entities_by_authored_ids(
        connection,
        scopes,
        [*request.scene_authored_entity_ids, *interlocutor_authored_ids],
    )
    per_alias_cap = request.ambiguous_alias_seed_cap
    return order_seed_ids(
        action_ids=match_aliases(request.action_text, alias_index, per_alias_cap),
        interlocutor_ids=_ids_for_authored(authored_rows, interlocutor_authored_ids),
        scene_ids=[
            *_ids_for_authored(authored_rows, request.scene_authored_entity_ids),
            *_scene_state_ids(request.scene),
        ],
        recent_ids=match_aliases(request.recent_text, alias_index, per_alias_cap),
    )


async def resolve_seeds(
    connection: AsyncConnection, request: SeedRequest
) -> list[EntityRow]:
    """Ordered seed entities, at most `seed_cap`. Only entities in the playthrough's
    own scopes can be returned; unknown or foreign ids are dropped. The player entity
    is seeded only if named or on the scene, never automatically."""
    scopes = build_scopes(request.playthrough_id, request.template_id)
    ordered_ids = await _collect_seed_ids(connection, request, scopes)
    rows = await entity_repo.get_entities(connection, scopes, ordered_ids)
    by_id = {row.entity_id: row for row in rows}
    resolved = [by_id[entity_id] for entity_id in ordered_ids if entity_id in by_id]
    return resolved[: request.seed_cap]

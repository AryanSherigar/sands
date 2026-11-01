"""Builds the extraction prompt input and validation context for a playthrough batch."""

from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from uuid import UUID

from app.config import Settings
from app.models.evidence import EventRow, SourceRow, SpanRow
from app.models.extraction import EXTRACTION_PROMPT_VERSION, ExtractionOutput
from app.models.facts import EntityRow
from app.models.jobs import ExtractionBatchRow
from app.models.retrieve import ExtractionContext, MemoryItem
from app.models.templates import ParticipantPayload, PlaythroughRow
from app.repositories import (
    entity_repo,
    event_repo,
    scene_repo,
    source_repo,
    span_repo,
)
from app.services.accepted_fact_mapper import parse_entity_attribute_path
from app.services.extraction_validator import (
    RejectedTarget,
    ValidationContext,
    normalize_predicate,
)
from app.services.ingest_common import sha256_hex
from app.services.retrieval_types import Scope, build_scopes
from psycopg import AsyncConnection

PROMPT_DIRECTORY = Path(__file__).parent.parent / "prompts"
REJECTED_EVENT_KIND = "rejected_mutation"
ACTION_SOURCE_KIND = "turn_action"
UNNAMED_PARTICIPANT_PREFIX = "Player"
PLAYER_CHARACTER_MARKER = "player character"
FIRST_PARTICIPANT_LETTER = ord("A")


@dataclass(frozen=True)
class BuiltInput:
    user_content: str
    validation: ValidationContext
    spans_by_label: dict[str, SpanRow]
    input_hash: str
    scopes: list[Scope]


@lru_cache
def load_system_prompt(version: str = EXTRACTION_PROMPT_VERSION) -> str:
    return (PROMPT_DIRECTORY / f"{version}.md").read_text(encoding="utf-8")


class ParticipantNames:
    """Display names from registration; unnamed participants become Player A, B, ..."""

    def __init__(self, participants: list[ParticipantPayload]) -> None:
        self._names = {item.participant_id: item.display_name for item in participants}
        self._fallbacks: dict[UUID, str] = {}

    def name_of(self, participant_id: UUID | None) -> str:
        if participant_id is None:
            return UNNAMED_PARTICIPANT_PREFIX
        if participant_id in self._names:
            return self._names[participant_id]
        if participant_id not in self._fallbacks:
            letter = chr(FIRST_PARTICIPANT_LETTER + len(self._fallbacks))
            self._fallbacks[participant_id] = f"{UNNAMED_PARTICIPANT_PREFIX} {letter}"
        return self._fallbacks[participant_id]


def _event_line(event: EventRow) -> str:
    payload = event.payload
    if event.event_kind == REJECTED_EVENT_KIND:
        return f"REJECTED {payload.get('tool_name')} {payload.get('arguments')}"
    return f"ACCEPTED {event.event_kind} {payload.get('key')}: {payload.get('before')} -> {payload.get('after')}"


def _turn_block(
    sequence: int,
    sources: list[SourceRow],
    spans: list[SpanRow],
    events: list[EventRow],
    names: ParticipantNames,
) -> str:
    kind_by_source = {source.source_id: source for source in sources}
    actor = next(
        (
            s.actor_participant_id
            for s in sources
            if s.source_kind == ACTION_SOURCE_KIND
        ),
        None,
    )
    lines = [f"### Turn {sequence} (actor: {names.name_of(actor)})"]
    for span in spans:
        kind = kind_by_source[span.source_id].source_kind.removeprefix("turn_")
        lines.append(f"{span.label} [{kind}] {span.text}")
    lines.extend(_event_line(event) for event in events)
    return "\n".join(lines)


def _render_turns(
    sources: list[SourceRow],
    spans: list[SpanRow],
    events: list[EventRow],
    names: ParticipantNames,
) -> str:
    sequences = sorted({span.sequence for span in spans})
    return "\n\n".join(
        _turn_block(
            sequence,
            [s for s in sources if s.sequence == sequence],
            [s for s in spans if s.sequence == sequence],
            [e for e in events if e.sequence == sequence],
            names,
        )
        for sequence in sequences
    )


def _render_context(context: ExtractionContext, *, has_facts: bool = True) -> str:
    kinds = ("fact", "commitment") if has_facts else ("commitment",)
    lines = [
        f"[{item.kind} {item.item_id}] {item.text}"
        for item in context.items
        if item.kind in kinds
    ]
    return "\n".join(lines) or "(none)"


def render_roster(roster: list[EntityRow]) -> str:
    lines = [
        f"{entity.entity_id} | {entity.entity_type} | {entity.canonical_name}"
        + (f" | {PLAYER_CHARACTER_MARKER}" if entity.is_player else "")
        for entity in roster
    ]
    return "\n".join(lines) or "(none)"


def _render_tracked(tracked_fields: list[str]) -> str:
    return "\n".join(f"- {name}" for name in tracked_fields) or "(none)"


def render_user_content(
    turns: str, context: str, roster: str, tracked: str, scene: str
) -> str:
    return (
        f"TRACKED STATE (never extract these):\n{tracked}\n\n"
        f"ROSTER (id | type | name):\n{roster}\n\n"
        f"CONTEXT (existing facts and commitments):\n{context}\n\n"
        f"CURRENT SCENE (before these turns):\n{scene}\n\n"
        f"TURNS:\n{turns}"
    )


async def _scene_entity_ids(
    connection: AsyncConnection, playthrough_id: UUID, at_seq: int
) -> list[UUID]:
    scene = await scene_repo.get_scene_at(connection, playthrough_id, at_seq)
    if scene is None:
        return []
    location = [scene.location_entity_id] if scene.location_entity_id else []
    return [*location, *scene.present_entity_ids]


def _seed_entity_ids(
    spans: list[SpanRow], scene_ids: list[UUID], playthrough: PlaythroughRow
) -> list[UUID]:
    mentioned = [entity_id for span in spans for entity_id in span.entity_ids]
    player = [playthrough.player_entity_id] if playthrough.player_entity_id else []
    return list(dict.fromkeys([*mentioned, *scene_ids, *player]))


def _roster_ids(seeds: list[UUID], context: ExtractionContext, cap: int) -> list[UUID]:
    return list(dict.fromkeys([*seeds, *context.entity_ids]))[:cap]


def _rejected_path(event: EventRow) -> str:
    arguments = event.payload.get("arguments")
    if not isinstance(arguments, dict):
        return ""
    return str(arguments.get("path", ""))


async def _rejected_targets(
    connection: AsyncConnection, playthrough: PlaythroughRow, events: list[EventRow]
) -> frozenset[RejectedTarget]:
    parsed = [
        parse_entity_attribute_path(_rejected_path(event))
        for event in events
        if event.event_kind == REJECTED_EVENT_KIND
    ]
    pairs = [pair for pair in parsed if pair is not None]
    scopes = build_scopes(playthrough.playthrough_id, playthrough.template_id)
    rows = await entity_repo.get_entities_by_authored_ids(
        connection, scopes, [authored_id for authored_id, _ in pairs]
    )
    memory_id_of = {row.authored_entity_id: row.entity_id for row in rows}
    return frozenset(
        RejectedTarget(str(memory_id_of[authored_id]), normalize_predicate(attribute))
        for authored_id, attribute in pairs
        if authored_id in memory_id_of
    )


def _supersedable_fact_ids(items: list[MemoryItem]) -> frozenset[str]:
    return frozenset(
        str(item.item_id)
        for item in items
        if item.kind == "fact" and item.authority != "accepted"
    )


def _commitment_ids(items: list[MemoryItem]) -> frozenset[str]:
    return frozenset(str(item.item_id) for item in items if item.kind == "commitment")


@dataclass(frozen=True)
class BatchRows:
    spans: list[SpanRow]
    sources: list[SourceRow]
    events: list[EventRow]


async def load_batch_rows(
    connection: AsyncConnection, batch: ExtractionBatchRow
) -> BatchRows:
    scope_id = batch.scope_id
    window = (batch.from_seq, batch.to_seq)
    return BatchRows(
        spans=await span_repo.list_spans_by_sequence(
            connection, "playthrough", scope_id, *window
        ),
        sources=await source_repo.list_sources(
            connection, "playthrough", scope_id, *window
        ),
        events=await event_repo.list_events(connection, scope_id, *window),
    )


async def seed_entity_ids_for(
    connection: AsyncConnection,
    batch: ExtractionBatchRow,
    playthrough: PlaythroughRow,
    rows: BatchRows,
) -> list[UUID]:
    scene_ids = await _scene_entity_ids(
        connection, playthrough.playthrough_id, batch.from_seq - 1
    )
    return _seed_entity_ids(rows.spans, scene_ids, playthrough)


async def build_playthrough_input(
    connection: AsyncConnection,
    batch: ExtractionBatchRow,
    playthrough: PlaythroughRow,
    context: ExtractionContext,
    rows: BatchRows,
    settings: Settings,
) -> BuiltInput:
    seeds = await seed_entity_ids_for(connection, batch, playthrough, rows)
    roster_ids = _roster_ids(seeds, context, settings.extraction_roster_cap)
    scopes = build_scopes(playthrough.playthrough_id, playthrough.template_id)
    roster = await entity_repo.get_entities(connection, scopes, roster_ids)
    rejected = await _rejected_targets(connection, playthrough, rows.events)
    return _assemble(batch, playthrough, context, rows, roster, rejected, settings)


def _validation_context(
    playthrough: PlaythroughRow,
    context: ExtractionContext,
    rows: BatchRows,
    roster: list[EntityRow],
    rejected: frozenset[RejectedTarget],
) -> ValidationContext:
    return ValidationContext(
        batch_labels=frozenset(span.label for span in rows.spans),
        roster_entity_ids=frozenset(str(entity.entity_id) for entity in roster),
        supersedable_fact_ids=_supersedable_fact_ids(context.items),
        open_commitment_ids=_commitment_ids(context.items),
        tracked_predicates=frozenset(
            normalize_predicate(field) for field in playthrough.tracked_fields
        ),
        rejected_targets=rejected,
    )


def _assemble(
    batch: ExtractionBatchRow,
    playthrough: PlaythroughRow,
    context: ExtractionContext,
    rows: BatchRows,
    roster: list[EntityRow],
    rejected: frozenset[RejectedTarget],
    settings: Settings,
) -> BuiltInput:
    names = ParticipantNames(playthrough.participants)
    user_content = render_user_content(
        turns=_render_turns(rows.sources, rows.spans, rows.events, names),
        context=_render_context(
            context, has_facts=settings.extraction_context_has_facts
        ),
        roster=render_roster(roster),
        tracked=_render_tracked(playthrough.tracked_fields),
        scene="(see ROSTER and CONTEXT)",
    )
    return BuiltInput(
        user_content=user_content,
        validation=_validation_context(playthrough, context, rows, roster, rejected),
        spans_by_label={span.label: span for span in rows.spans},
        input_hash=sha256_hex(f"{batch.model}:{batch.prompt_version}:{user_content}"),
        scopes=build_scopes(playthrough.playthrough_id, playthrough.template_id),
    )


async def with_alias_context(
    connection: AsyncConnection,
    scopes: list[Scope],
    validation: ValidationContext,
    output: ExtractionOutput,
) -> ValidationContext:
    names = {
        entity_repo.normalize_alias(name)
        for entity in output.new_entities
        for name in [entity.name, *entity.aliases]
    }
    matches = await entity_repo.find_entities_by_alias(
        connection, scopes, sorted(names)
    )
    extracted: dict[str, list[str]] = {}
    authored: set[str] = set()
    for alias, entity in matches:
        if entity.provenance == "authored":
            authored.add(alias)
        else:
            extracted.setdefault(alias, []).append(str(entity.entity_id))
    return replace(
        validation, extracted_aliases=extracted, authored_aliases=frozenset(authored)
    )

"""Fixture builders for template/playthrough/evidence repo tests, built through the
app's own idempotent repo functions rather than plain SQL."""

from uuid import UUID, uuid4

from app.models.common import EventKind, ScopeKind, SourceKind
from app.models.evidence import EventCreate, SourceCreate, SpanCreate
from app.models.templates import (
    PlaythroughCreate,
    PlaythroughRow,
    TemplateCreate,
    TemplateRow,
)
from app.repositories.playthrough_repo import register_playthrough
from app.repositories.source_repo import create_source
from app.repositories.template_repo import create_template
from psycopg import AsyncConnection

DEFAULT_MODE = "master"
DEFAULT_DIRECT_STATUS = "ready"
DEFAULT_ENRICHMENT_STATUS = "not_needed"
DEFAULT_SOURCE_KIND: SourceKind = "authored_lore"
DEFAULT_EVENT_KIND: EventKind = "roll"


async def make_template(
    connection: AsyncConnection,
    *,
    scenario_id: UUID | None = None,
    publish_revision: int = 1,
) -> TemplateRow:
    return await create_template(
        connection,
        TemplateCreate(
            scenario_id=scenario_id or uuid4(),
            publish_revision=publish_revision,
            mode=DEFAULT_MODE,
            direct_status=DEFAULT_DIRECT_STATUS,
            enrichment_status=DEFAULT_ENRICHMENT_STATUS,
            content_hash="hash",
        ),
    )


async def make_playthrough(
    connection: AsyncConnection,
    *,
    playthrough_id: UUID | None = None,
    template_id: UUID | None = None,
) -> PlaythroughRow:
    return await register_playthrough(
        connection,
        PlaythroughCreate(
            playthrough_id=playthrough_id or uuid4(),
            template_id=template_id,
        ),
    )


async def make_source(
    connection: AsyncConnection,
    *,
    scope_kind: ScopeKind,
    scope_id: UUID,
    source_kind: SourceKind = DEFAULT_SOURCE_KIND,
    source_ref: str = "ref-1",
    sequence: int = 0,
    content: str = "content",
):
    return await create_source(
        connection,
        SourceCreate(
            scope_kind=scope_kind,
            scope_id=scope_id,
            source_kind=source_kind,
            source_ref=source_ref,
            sequence=sequence,
            content=content,
            content_hash="hash",
        ),
    )


def build_span(
    *,
    source_id: UUID,
    scope_kind: ScopeKind,
    scope_id: UUID,
    ordinal: int = 0,
    sequence: int = 0,
    text: str = "text",
    label: str = "L1",
) -> SpanCreate:
    return SpanCreate(
        source_id=source_id,
        scope_kind=scope_kind,
        scope_id=scope_id,
        sequence=sequence,
        ordinal=ordinal,
        start_offset=0,
        end_offset=len(text),
        text=text,
        token_count=len(text.split()) or 1,
        label=label,
    )


def build_event(
    *,
    playthrough_id: UUID,
    turn_id: UUID | None = None,
    sequence: int = 1,
    event_kind: EventKind = DEFAULT_EVENT_KIND,
    event_key: str = "key-1",
) -> EventCreate:
    return EventCreate(
        playthrough_id=playthrough_id,
        sequence=sequence,
        turn_id=turn_id or uuid4(),
        event_kind=event_kind,
        event_key=event_key,
        is_accepted=True,
        payload={},
    )

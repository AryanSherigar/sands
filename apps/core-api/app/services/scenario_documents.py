"""Derives the plain-text scenario fields the narrator reads from lore documents.

The document is the single source: whenever one is written, its rendering
overwrites the plain-text field it feeds.
"""

from app.models.lore_document import LoreDocument
from app.models.world_data_documents import (
    KEY_OPENING_DOCUMENT,
    KEY_PREMISE,
    KEY_PREMISE_DOCUMENT,
    KEY_WORLD_LORE,
    KEY_WORLD_LORE_DOCUMENT,
)
from app.services.lore_render import render_lore_document

FIELD_NARRATOR_PERSONA = "narrator_persona"
FIELD_NARRATOR_PERSONA_DOCUMENT = "narrator_persona_document"
FIELD_OPENING_SCENE = "opening_scene"
FIELD_WORLD_DATA = "world_data"
WORLD_DATA_RENDERED_KEYS = {
    KEY_PREMISE_DOCUMENT: KEY_PREMISE,
    KEY_WORLD_LORE_DOCUMENT: KEY_WORLD_LORE,
}


def _render_raw_document(raw_document: object) -> str:
    return render_lore_document(LoreDocument.model_validate(raw_document))


def _render_world_data(world_data: dict[str, object]) -> dict[str, object]:
    rendered = dict(world_data)
    for document_key, text_key in WORLD_DATA_RENDERED_KEYS.items():
        if rendered.get(document_key) is not None:
            rendered[text_key] = _render_raw_document(rendered[document_key])
    return rendered


def _apply_world_data_documents(fields: dict[str, object]) -> None:
    world_data = fields.get(FIELD_WORLD_DATA)
    if not isinstance(world_data, dict):
        return
    fields[FIELD_WORLD_DATA] = _render_world_data(world_data)
    opening_document = world_data.get(KEY_OPENING_DOCUMENT)
    if opening_document is not None:
        fields[FIELD_OPENING_SCENE] = _render_raw_document(opening_document) or None


def _apply_persona_document(fields: dict[str, object]) -> None:
    persona_document = fields.get(FIELD_NARRATOR_PERSONA_DOCUMENT)
    if persona_document is None:
        return
    document = LoreDocument.model_validate(persona_document)
    fields[FIELD_NARRATOR_PERSONA_DOCUMENT] = document.model_dump()
    fields[FIELD_NARRATOR_PERSONA] = render_lore_document(document) or None


def apply_rendered_documents(fields: dict[str, object]) -> None:
    """Mutates a create or update field map, rendering every document it carries."""
    _apply_world_data_documents(fields)
    _apply_persona_document(fields)

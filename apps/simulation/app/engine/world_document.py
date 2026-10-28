import json

from app.engine.world_upgrade import (
    LEGACY_WORLD_SCHEMA_VERSION,
    PREVIOUS_WORLD_SCHEMA_VERSION,
    upgrade_v4_document,
    upgrade_v5_document,
)
from app.exceptions.world_exceptions import (
    InvalidWorldDocumentError,
    UnsupportedWorldSchemaVersionError,
)
from app.models.world_state import WORLD_SCHEMA_VERSION, WorldState

MISSING_SCHEMA_VERSION = 0


def world_from_document(document: dict[str, object]) -> WorldState:
    found = document.get("schema_version", MISSING_SCHEMA_VERSION)
    if found == LEGACY_WORLD_SCHEMA_VERSION:
        return upgrade_v4_document(document)
    if found == PREVIOUS_WORLD_SCHEMA_VERSION:
        return upgrade_v5_document(document)
    if found != WORLD_SCHEMA_VERSION:
        raise UnsupportedWorldSchemaVersionError(
            found=found if isinstance(found, int) else MISSING_SCHEMA_VERSION,
            supported=WORLD_SCHEMA_VERSION,
        )
    return WorldState.model_validate(document)


def parse_world_document(raw_json: str) -> WorldState:
    document = json.loads(raw_json)
    if not isinstance(document, dict):
        raise InvalidWorldDocumentError()
    return world_from_document(document)

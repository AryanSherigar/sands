"""Which entities are on scene this turn (master mode).

One seam on purpose: retrieval seeds, the state block, active cards and
narrator instructions all read it, so an explicit scene list can replace the
heuristic later by changing this function only.
"""

STATE_KEY_NARRATIVE = "narrative"
STATE_KEY_DISCOVERED_LOCATIONS = "discovered_location_ids"
INTERNAL_KEY_PREFIX = "_"


def get_on_scene_entity_ids(
    state: dict[str, object], snapshot: dict[str, object]
) -> set[str]:
    """Entity ids that any entity_ref-shaped value in state currently points at.

    Bookkeeping keys (the narrative log, internal `_` keys, the discovered-
    locations list) are skipped: a location the player has merely visited is not
    where they are now. The current location is `current_location_id`, which
    this scan does include.
    """
    known_entity_ids = _known_entity_ids(snapshot)
    scannable = {
        key: value for key, value in state.items() if not _is_bookkeeping_key(key)
    }
    return _find_entity_ref_values(scannable, known_entity_ids)


def _known_entity_ids(snapshot: dict[str, object]) -> set[str]:
    entities = snapshot.get("entities", []) or []
    return {
        str(entity.get("entity_id")) for entity in entities if isinstance(entity, dict)
    }


def _is_bookkeeping_key(key: str) -> bool:
    return key.startswith(INTERNAL_KEY_PREFIX) or key in (
        STATE_KEY_NARRATIVE,
        STATE_KEY_DISCOVERED_LOCATIONS,
    )


def _find_entity_ref_values(node: object, known_entity_ids: set[str]) -> set[str]:
    if isinstance(node, str):
        return {node} if node in known_entity_ids else set()
    if isinstance(node, dict):
        return _union(node.values(), known_entity_ids)
    if isinstance(node, list):
        return _union(node, known_entity_ids)
    return set()


def _union(nodes: object, known_entity_ids: set[str]) -> set[str]:
    found: set[str] = set()
    for node in nodes:
        found |= _find_entity_ref_values(node, known_entity_ids)
    return found

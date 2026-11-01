"""Unit tests for app/turn/on_scene.py."""

import uuid

from app.turn.on_scene import get_on_scene_entity_ids


def _snapshot(*entity_ids: uuid.UUID) -> dict[str, object]:
    return {"entities": [{"entity_id": str(entity_id)} for entity_id in entity_ids]}


def test_finds_entity_refs_anywhere_in_state() -> None:
    tavern, mara, unrelated = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    state = {
        "current_location_id": str(tavern),
        "quest": {"giver": str(mara), "tags": ["x"]},
        "flags": {"note": str(unrelated)},
    }

    found = get_on_scene_entity_ids(state, _snapshot(tavern, mara))

    assert found == {str(tavern), str(mara)}


def test_ignores_strings_that_are_not_known_entities() -> None:
    known = uuid.uuid4()

    found = get_on_scene_entity_ids(
        {"player": {"name": "Kaelen", "home": str(uuid.uuid4())}}, _snapshot(known)
    )

    assert found == set()


def test_reads_entity_refs_inside_lists() -> None:
    first, second = uuid.uuid4(), uuid.uuid4()

    found = get_on_scene_entity_ids(
        {"party": [str(first), {"member": str(second)}]}, _snapshot(first, second)
    )

    assert found == {str(first), str(second)}


def test_skips_bookkeeping_keys() -> None:
    current, visited, logged, internal = (uuid.uuid4() for _ in range(4))
    state = {
        "current_location_id": str(current),
        "discovered_location_ids": [str(visited), str(current)],
        "narrative": {"note": str(logged)},
        "_pending_check": {"target": str(internal)},
    }

    found = get_on_scene_entity_ids(
        state, _snapshot(current, visited, logged, internal)
    )

    assert found == {str(current)}


def test_missing_entities_in_snapshot_means_nothing_is_on_scene() -> None:
    assert get_on_scene_entity_ids({"a": str(uuid.uuid4())}, {}) == set()

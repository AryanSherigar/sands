import json

import pytest
from app.engine.hashing import world_hash
from app.engine.world_document import parse_world_document, world_from_document
from app.exceptions.world_exceptions import (
    InvalidWorldDocumentError,
    UnsupportedWorldSchemaVersionError,
)
from app.models.world_army import MarchState
from app.models.world_state import WORLD_SCHEMA_VERSION

from tests.models.builders import make_world


def test_world_round_trips_through_the_parser() -> None:
    world = make_world()
    assert parse_world_document(world.model_dump_json()) == world


def test_other_schema_version_is_refused_with_found_version() -> None:
    document = json.loads(make_world().model_dump_json())
    document["schema_version"] = WORLD_SCHEMA_VERSION + 1
    with pytest.raises(UnsupportedWorldSchemaVersionError) as error:
        parse_world_document(json.dumps(document))
    assert error.value.found == WORLD_SCHEMA_VERSION + 1


def test_missing_schema_version_is_refused_as_zero() -> None:
    document = json.loads(make_world().model_dump_json())
    del document["schema_version"]
    with pytest.raises(UnsupportedWorldSchemaVersionError) as error:
        parse_world_document(json.dumps(document))
    assert error.value.found == 0


def test_non_object_document_is_refused() -> None:
    with pytest.raises(InvalidWorldDocumentError):
        parse_world_document("[1, 2]")


def test_world_from_document_refuses_a_foreign_version() -> None:
    document = json.loads(make_world().model_dump_json())
    document["schema_version"] = WORLD_SCHEMA_VERSION + 1
    with pytest.raises(UnsupportedWorldSchemaVersionError):
        world_from_document(document)


def test_world_with_a_march_in_progress_survives_a_document_round_trip() -> None:
    world = make_world()
    world.armies["army_a"].march = MarchState(
        from_id="ashford", to_id="carrow_vale", route=[], leg_progress=55
    )
    restored = parse_world_document(world.model_dump_json())
    assert restored == world
    assert world_hash(restored) == world_hash(world)


def test_literal_v4_upgrade_preserves_state_without_inventing_exchanges() -> None:
    from pathlib import Path

    document = json.loads(
        (Path(__file__).parents[1] / "fixtures/world_v4.json").read_text()
    )
    restored = world_from_document(document)
    assert restored.schema_version == 6
    assert restored.clock.turn == 2
    assert restored.rng.seed == 42
    assert next(iter(restored.factions.values())).treasury == 140
    assert restored.armies["army_a"].fatigue == 0
    assert restored.battles[0].attacker_army_ids == ["army_a"]
    assert restored.battles[0].defender_army_ids == ["army_b"]
    assert restored.battles[0].total_exchanges == 0
    assert restored.accepted_commands == []
    assert "pending_battles" not in restored.model_dump()
    assert document["schema_version"] == 4


def test_v4_captive_upgrade_retains_unknown_composition_explicitly() -> None:
    from pathlib import Path

    document = json.loads(
        (Path(__file__).parents[1] / "fixtures/world_v4.json").read_text()
    )
    document["prisoners"] = [
        {
            "id": "prisoner_1",
            "held_by_id": "house_ashford",
            "origin_faction_id": "house_carrow",
            "kind": "troops",
            "troop_count": 73,
            "character_id": None,
        }
    ]
    restored = world_from_document(document)
    prisoner = restored.prisoners[0]
    assert prisoner.troop_count == 73
    assert prisoner.is_legacy_aggregate
    assert prisoner.origin_battle_id is None
    assert prisoner.troops_by_type == {}
    assert (
        parse_world_document(restored.model_dump_json()).prisoners == restored.prisoners
    )


def test_v4_resolved_battle_preserves_missing_historical_army_reference() -> None:
    from pathlib import Path

    document = json.loads(
        (Path(__file__).parents[1] / "fixtures/world_v4.json").read_text()
    )
    document["pending_battles"][0]["status"] = "resolved"
    del document["armies"]["army_b"]
    restored = world_from_document(document)
    assert restored.battles[0].defender_army_ids == ["army_b"]
    assert restored.battles[0].defender_lead_faction_id is None
    assert restored.battles[0].total_exchanges == 0

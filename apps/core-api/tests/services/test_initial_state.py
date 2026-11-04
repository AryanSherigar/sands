import random
import uuid

import pytest
from app.exceptions.playthrough_exceptions import InvalidSchemaInitialError
from app.services.initial_state import materialise_initial_state

NO_ENTITIES: list[dict[str, object]] = []


def _materialise(schema, entities=NO_ENTITIES, tools=()):
    return materialise_initial_state(schema, entities, random.Random(1), tools)


def test_top_level_initials_are_applied_and_fields_without_initial_omitted():
    schema = {
        "sanity": {"type": "number", "initial": 85},
        "alarm": {"type": "boolean", "initial": False},
        "mood": {"type": "enum", "options": ["calm", "tense"], "initial": "calm"},
        "note": {"type": "string"},
    }

    assert _materialise(schema) == {"sanity": 85, "alarm": False, "mood": "calm"}


def test_object_fields_recurse_and_empty_groups_are_dropped():
    schema = {
        "player": {
            "type": "object",
            "fields": {"health": {"type": "number", "initial": 100}},
        },
        "flags": {"type": "object", "fields": {"seen": {"type": "boolean"}}},
    }

    assert _materialise(schema) == {"player": {"health": 100}}


def test_reserved_location_keys_are_skipped():
    schema = {
        "current_location_id": {"type": "entity_ref", "initial": "x"},
        "discovered_location_ids": {"type": "list", "initial": ["x"]},
        "sanity": {"type": "number", "initial": 1},
    }

    assert _materialise(schema) == {"sanity": 1}


def test_entity_attribute_initials_land_under_entities_bucket():
    entity_id = str(uuid.uuid4())
    entities = [
        {
            "entity_id": entity_id,
            "attributes_schema": {"trust": {"type": "number", "initial": 3}},
        },
        {"entity_id": str(uuid.uuid4()), "attributes_schema": {}},
    ]

    result = _materialise({}, entities)

    assert result == {"entities": {entity_id: {"trust": 3}}}


def test_initial_random_is_ignored_without_the_rule_checks_tool():
    schema = {
        "rule": {
            "type": "enum",
            "options": ["r4", "r6"],
            "initial_random": ["r4", "r6"],
        }
    }

    assert _materialise(schema, tools=()) == {}


def test_wrong_typed_initial_fails_with_clear_error():
    schema = {"sanity": {"type": "number", "initial": "lots"}}

    with pytest.raises(InvalidSchemaInitialError) as raised:
        _materialise(schema)

    assert "sanity" in raised.value.message


def test_bool_is_not_accepted_as_number():
    with pytest.raises(InvalidSchemaInitialError):
        _materialise({"sanity": {"type": "number", "initial": True}})


def test_enum_initial_must_be_an_option():
    schema = {"mood": {"type": "enum", "options": ["calm"], "initial": "wild"}}

    with pytest.raises(InvalidSchemaInitialError):
        _materialise(schema)


def test_number_initial_outside_bounds_fails():
    schema = {"sanity": {"type": "number", "min": 0, "max": 100, "initial": 150}}

    with pytest.raises(InvalidSchemaInitialError):
        _materialise(schema)


def test_nested_failure_names_the_dotted_path():
    schema = {
        "player": {
            "type": "object",
            "fields": {"health": {"type": "number", "initial": "x"}},
        }
    }

    with pytest.raises(InvalidSchemaInitialError) as raised:
        _materialise(schema)

    assert "player.health" in raised.value.message


def test_result_does_not_alias_schema_values():
    schema = {"tags": {"type": "list", "initial": ["a"]}}

    result = _materialise(schema)
    result["tags"].append("b")

    assert schema["tags"]["initial"] == ["a"]


RANDOM_SCHEMA = {
    "rule": {
        "type": "enum",
        "options": ["r4", "r6", "r9"],
        "initial_random": ["r4", "r6"],
    },
    "flags": {
        "type": "object",
        "fields": {
            "door": {
                "type": "enum",
                "options": ["open", "shut"],
                "initial_random": ["open", "shut"],
            }
        },
    },
}


def test_initial_random_draws_one_value_per_field_with_the_tool_on():
    state = _materialise(RANDOM_SCHEMA, tools=("rule_checks",))

    assert state["rule"] in ("r4", "r6")
    assert state["flags"]["door"] in ("open", "shut")


def test_initial_random_draw_is_deterministic_for_one_seed():
    first = materialise_initial_state(
        RANDOM_SCHEMA, [], random.Random(7), ["rule_checks"]
    )
    second = materialise_initial_state(
        RANDOM_SCHEMA, [], random.Random(7), ["rule_checks"]
    )

    assert first == second


def test_initial_random_varies_across_seeds():
    draws = {
        materialise_initial_state(
            RANDOM_SCHEMA, [], random.Random(seed), ["rule_checks"]
        )["rule"]
        for seed in range(40)
    }

    assert draws == {"r4", "r6"}


def test_initial_random_overrides_a_plain_initial():
    schema = {
        "rule": {
            "type": "enum",
            "options": ["r4", "r6"],
            "initial": "r4",
            "initial_random": ["r6"],
        }
    }

    assert _materialise(schema, tools=("rule_checks",)) == {"rule": "r6"}


def test_initial_random_value_outside_the_enum_fails_loudly():
    schema = {
        "rule": {"type": "enum", "options": ["r4"], "initial_random": ["r9"]},
    }

    with pytest.raises(InvalidSchemaInitialError):
        _materialise(schema, tools=("rule_checks",))

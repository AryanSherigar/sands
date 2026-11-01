"""Visibility helper tests. The `VISIBLE_STATE_CASES` table is duplicated verbatim
in apps/core-api/tests/services/test_state_visibility.py; keep both copies
identical."""

import pytest
from app.turn.state_visibility import visible_state

VISIBLE_STATE_CASES = [
    pytest.param(
        {"sanity": {"type": "number", "hidden": True}, "clock": {"type": "number"}},
        {"sanity": 40, "clock": 12},
        {"clock": 12},
        id="hidden-leaf-removed",
    ),
    pytest.param(
        {
            "secrets": {
                "type": "object",
                "hidden": True,
                "fields": {"code": {"type": "string"}},
            }
        },
        {"secrets": {"code": "1234"}, "other": 1},
        {"other": 1},
        id="hidden-group-removes-subtree",
    ),
    pytest.param(
        {"sanity": {"type": "number"}},
        {"sanity": 40},
        {"sanity": 40},
        id="absent-flag-is-visible",
    ),
    pytest.param(
        {"sanity": {"type": "number", "hidden": False}},
        {"sanity": 40},
        {"sanity": 40},
        id="false-flag-is-visible",
    ),
    pytest.param(
        {
            "player": {
                "type": "object",
                "fields": {
                    "health": {"type": "number"},
                    "dread": {"type": "number", "hidden": True},
                },
            }
        },
        {"player": {"health": 9, "dread": 3}},
        {"player": {"health": 9}},
        id="nested-hidden-leaf-removed",
    ),
    pytest.param(
        {},
        {
            "a": 1,
            "_fired_conditions": ["c1"],
            "_check_queue": ["k"],
            "_check_edges": ["k"],
            "_check_reopens": {"k": 1},
        },
        {"a": 1},
        id="new-system-keys-stripped",
    ),
    pytest.param(
        {},
        {
            "_pending_check": {"check_id": "x"},
            "_pending_minigame": {"minigame_id": "m"},
            "_last_changed_fields": ["a"],
            "_active_conditions": ["c"],
        },
        {
            "_pending_check": {"check_id": "x"},
            "_pending_minigame": {"minigame_id": "m"},
            "_last_changed_fields": ["a"],
            "_active_conditions": ["c"],
        },
        id="existing-system-keys-kept",
    ),
    pytest.param(
        {"sanity": {"type": "number", "hidden": True}},
        {"entities": {"e1": {"sanity": 5}}},
        {"entities": {"e1": {"sanity": 5}}},
        id="entity-attributes-not-filtered-by-root-schema",
    ),
    pytest.param(
        {"sanity": {"type": "number", "hidden": True}},
        {"clock": 3},
        {"clock": 3},
        id="hidden-field-absent-from-state-is-fine",
    ),
]


@pytest.mark.parametrize(("schema", "state", "expected"), VISIBLE_STATE_CASES)
def test_visible_state(schema, state, expected):
    assert visible_state(state, schema) == expected


def test_visible_state_does_not_mutate_its_inputs():
    schema = {"sanity": {"type": "number", "hidden": True}}
    state = {"sanity": 1, "_check_queue": ["k"]}

    visible_state(state, schema)

    assert state == {"sanity": 1, "_check_queue": ["k"]}
    assert schema == {"sanity": {"type": "number", "hidden": True}}


def test_case_table_is_identical_to_core_api_copy():
    from pathlib import Path

    core_test = (
        Path(__file__).resolve().parents[3]
        / "core-api"
        / "tests"
        / "services"
        / "test_state_visibility.py"
    ).read_text()
    own_test = Path(__file__).read_text()

    def table(source: str) -> str:
        start = source.index("VISIBLE_STATE_CASES = [")
        return source[start : source.index("\n]\n", start)]

    assert table(own_test) == table(core_test)


from app.turn.state_visibility import is_hidden_path  # noqa: E402

HIDDEN_SCHEMA = {
    "dread": {"type": "number", "hidden": True},
    "clock": {"type": "number"},
    "secrets": {
        "type": "object",
        "hidden": True,
        "fields": {"code": {"type": "string"}},
    },
    "player": {
        "type": "object",
        "fields": {
            "fear": {"type": "number", "hidden": True},
            "hp": {"type": "number"},
        },
    },
}


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("dread", True),
        ("clock", False),
        ("secrets", True),
        ("secrets.code", True),
        ("player.fear", True),
        ("player.hp", False),
        ("player", False),
        ("unknown.path", False),
        ("", False),
    ],
)
def test_is_hidden_path(path, expected):
    assert is_hidden_path(HIDDEN_SCHEMA, path) is expected

from app.turn.steps.state_update_builder import build_state_update

SNAPSHOT = {
    "state_schema": {
        "clock": {"type": "number"},
        "sanity": {"type": "number", "hidden": True},
        "player": {
            "type": "object",
            "fields": {
                "health": {"type": "number"},
                "dread": {"type": "number", "hidden": True},
            },
        },
    }
}


def test_state_is_the_visible_subset_of_the_working_state() -> None:
    state = {
        "clock": 30,
        "sanity": 12,
        "player": {"health": 9, "dread": 4},
        "_fired_conditions": ["c1"],
        "_check_queue": ["q"],
    }

    payload = build_state_update(SNAPSHOT, state)

    assert payload == {"state": {"clock": 30, "player": {"health": 9}}}


def test_pending_markers_the_client_needs_are_kept() -> None:
    state = {"clock": 1, "_pending_check": {"check_id": "x"}}

    payload = build_state_update(SNAPSHOT, state)

    assert payload["state"]["_pending_check"] == {"check_id": "x"}


def test_builder_does_not_mutate_the_working_state() -> None:
    state = {"clock": 1, "sanity": 5}

    build_state_update(SNAPSHOT, state)

    assert state == {"clock": 1, "sanity": 5}


def test_a_snapshot_without_a_schema_still_works() -> None:
    assert build_state_update({}, {"clock": 1}) == {"state": {"clock": 1}}

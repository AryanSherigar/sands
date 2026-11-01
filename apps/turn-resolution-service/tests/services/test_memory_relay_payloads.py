"""Unit tests for memory_relay_payloads.py (no database, no HTTP)."""

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from app.exceptions.memory_exceptions import InvalidOutboxPayloadError
from app.services.memory_relay_payloads import build_relay_batch


def _row(outbox_id: int, kind: str, sequence: int, turn_id=None, payload=None):
    return SimpleNamespace(
        outbox_id=outbox_id,
        item_kind=kind,
        sequence=sequence,
        turn_id=turn_id,
        payload=payload,
    )


def _turn_log(turn_id, turn_number=1, participant_id="default", **overrides):
    values = {
        "turn_id": turn_id,
        "turn_number": turn_number,
        "participant_id": uuid.uuid4()
        if participant_id == "default"
        else participant_id,
        "action_mode": "say",
        "action_text": "hello",
        "narration_text": "world",
        "accepted_delta": {},
        "tool_calls": [],
        "created_at": datetime(2026, 10, 26, tzinfo=UTC),
    }
    values.update(overrides)
    return SimpleNamespace(**values)


_REGISTER_PAYLOAD = {
    "scenario_id": str(uuid.uuid4()),
    "publish_revision": 2,
    "player_entity": None,
    "setup_facts": [],
}


def test_register_turn_and_flush_rows_become_items_in_order() -> None:
    turn_id = uuid.uuid4()
    rows = [
        _row(1, "register_playthrough", 0, payload=_REGISTER_PAYLOAD),
        _row(2, "turn", 1, turn_id=turn_id),
        _row(3, "flush", 1),
    ]

    batch = build_relay_batch(rows, {turn_id: _turn_log(turn_id)})

    assert [(item.item_kind, item.sequence) for item in batch.items] == [
        ("register_playthrough", 0),
        ("turn", 1),
        ("flush", 1),
    ]
    assert batch.sendable_row_ids == [1, 2, 3]
    assert batch.orphan_rows == []


def test_turn_payload_carries_log_fields() -> None:
    turn_id = uuid.uuid4()
    participant_id = uuid.uuid4()
    log = _turn_log(
        turn_id,
        turn_number=4,
        participant_id=participant_id,
        accepted_delta={
            "items": [
                {"kind": "state_mutation", "key": "gold", "before": 1, "after": 2}
            ]
        },
    )

    batch = build_relay_batch([_row(1, "turn", 4, turn_id=turn_id)], {turn_id: log})

    payload = batch.items[0].payload
    assert (payload.turn_id, payload.turn_number, payload.participant_id) == (
        turn_id,
        4,
        participant_id,
    )
    assert (payload.action_mode, payload.action_text, payload.narration_text) == (
        "say",
        "hello",
        "world",
    )
    assert payload.accepted_delta.items[0].key == "gold"
    assert payload.created_at == log.created_at


def test_null_narration_becomes_empty_string() -> None:
    turn_id = uuid.uuid4()

    batch = build_relay_batch(
        [_row(1, "turn", 1, turn_id=turn_id)],
        {turn_id: _turn_log(turn_id, narration_text=None)},
    )

    assert batch.items[0].payload.narration_text == ""


def test_only_invalid_mutation_calls_become_rejected_calls() -> None:
    turn_id = uuid.uuid4()
    tool_calls = [
        {
            "tool_name": "set_field",
            "arguments": {"path": "a"},
            "result": {"error": "x"},
            "is_valid": False,
        },
        {
            "tool_name": "set_field",
            "arguments": {"path": "b"},
            "result": {"success": True},
            "is_valid": True,
        },
        {
            "tool_name": "propose_check",
            "arguments": {},
            "result": {},
            "is_valid": False,
        },
        {"tool_name": "unknown_tool", "arguments": {}, "result": {}, "is_valid": False},
        "not-a-dict",
    ]

    batch = build_relay_batch(
        [_row(1, "turn", 1, turn_id=turn_id)],
        {turn_id: _turn_log(turn_id, tool_calls=tool_calls)},
    )

    [rejected] = batch.items[0].payload.rejected_calls
    assert rejected.tool_name == "set_field"
    assert rejected.arguments == {"path": "a"}
    assert rejected.result == {"error": "x"}


def test_missing_turn_log_is_an_orphan() -> None:
    batch = build_relay_batch([_row(7, "turn", 1, turn_id=uuid.uuid4())], {})

    assert batch.items == []
    assert batch.orphan_rows == [(7, "turn_log_missing")]


def test_null_participant_is_an_orphan() -> None:
    turn_id = uuid.uuid4()

    batch = build_relay_batch(
        [_row(8, "turn", 1, turn_id=turn_id)],
        {turn_id: _turn_log(turn_id, participant_id=None)},
    )

    assert batch.orphan_rows == [(8, "participant_missing")]


def test_orphans_do_not_block_later_rows() -> None:
    turn_id = uuid.uuid4()
    rows = [
        _row(1, "turn", 1, turn_id=uuid.uuid4()),
        _row(2, "turn", 2, turn_id=turn_id),
    ]

    batch = build_relay_batch(rows, {turn_id: _turn_log(turn_id, turn_number=2)})

    assert batch.sendable_row_ids == [2]
    assert batch.orphan_rows == [(1, "turn_log_missing")]


def test_invalid_register_payload_raises() -> None:
    with pytest.raises(InvalidOutboxPayloadError):
        build_relay_batch(
            [_row(1, "register_playthrough", 0, payload={"scenario_id": "nope"})], {}
        )


def test_malformed_stored_delta_raises() -> None:
    turn_id = uuid.uuid4()

    with pytest.raises(InvalidOutboxPayloadError):
        build_relay_batch(
            [_row(1, "turn", 1, turn_id=turn_id)],
            {turn_id: _turn_log(turn_id, accepted_delta={"items": "bad"})},
        )


def test_register_item_forwards_participants_and_tracked_fields() -> None:
    participant_id = uuid.uuid4()
    payload = {
        **_REGISTER_PAYLOAD,
        "participants": [
            {"participant_id": str(participant_id), "display_name": "Ada"}
        ],
        "tracked_fields": ["player.health"],
    }

    batch = build_relay_batch([_row(1, "register_playthrough", 0, payload=payload)], {})

    body = batch.items[0].payload.model_dump(mode="json")
    assert body["participants"] == [
        {"participant_id": str(participant_id), "display_name": "Ada"}
    ]
    assert body["tracked_fields"] == ["player.health"]


def test_participants_row_becomes_a_participants_item_at_its_sequence() -> None:
    participant_id = uuid.uuid4()
    row = _row(
        1,
        "participants",
        3,
        payload={
            "participants": [
                {"participant_id": str(participant_id), "display_name": "Bram"}
            ]
        },
    )

    batch = build_relay_batch([row], {})

    [item] = batch.items
    assert (item.item_kind, item.sequence) == ("participants", 3)
    assert item.payload.participants[0].display_name == "Bram"
    assert batch.sendable_row_ids == [1]


def test_invalid_participants_payload_raises() -> None:
    row = _row(1, "participants", 1, payload={"participants": "nope"})

    with pytest.raises(InvalidOutboxPayloadError):
        build_relay_batch([row], {})

"""Unit tests for response_streamer.py's pure SSE-formatting functions."""

import json
import uuid

from app.models.check_event import CheckEventPayload, CheckResolvedPayload
from app.models.turn_summary import StatChange, TurnSummaryPayload
from app.turn.steps.response_streamer import (
    build_sse_response,
    check_event,
    check_resolved_event,
    degraded_event,
    done_event,
    input_truncated_event,
    narration_event,
    turn_summary_event,
)
from sse_starlette.sse import EventSourceResponse


def test_narration_event_carries_chunk_as_data() -> None:
    event = narration_event("Hello, adventurer.")

    assert event.event == "narration"
    assert event.data == "Hello, adventurer."


def test_done_event_has_done_type() -> None:
    event = done_event()

    assert event.event == "done"


def test_degraded_event_carries_message() -> None:
    event = degraded_event("Your turn couldn't be saved.")

    assert event.event == "degraded"
    assert event.data == "Your turn couldn't be saved."


def test_turn_summary_event_serializes_payload_as_json() -> None:
    payload = TurnSummaryPayload(
        stat_changes=[
            StatChange(
                path="player.health", label="Health", before=100, after=85, delta=-15.0
            )
        ],
        active_conditions=["Bleeding Out"],
    )

    event = turn_summary_event(payload)

    assert event.event == "turn_summary"
    data = json.loads(event.data)
    assert data["active_conditions"] == ["Bleeding Out"]
    assert data["stat_changes"][0]["path"] == "player.health"
    assert data["inventory_changes"] == []


def test_check_event_serializes_payload_as_json() -> None:
    payload = CheckEventPayload(
        check_id="check-1", check_type="stealth", difficulty_class=15, reasoning="risky"
    )

    event = check_event(payload)

    assert event.event == "check"
    data = json.loads(event.data)
    assert data["check_id"] == "check-1"
    assert data["difficulty_class"] == 15


def test_check_resolved_event_serializes_payload_as_json() -> None:
    payload = CheckResolvedPayload(
        check_id="check-1",
        check_type="stealth",
        difficulty_class=15,
        resolved_roll=17,
        is_success=True,
    )

    event = check_resolved_event(payload)

    assert event.event == "check_resolved"
    data = json.loads(event.data)
    assert data["resolved_roll"] == 17
    assert data["is_success"] is True


async def test_build_sse_response_wraps_events_without_consuming_them() -> None:
    async def events():
        yield narration_event("chunk")
        yield done_event()

    response = await build_sse_response(events())

    assert isinstance(response, EventSourceResponse)


def test_input_truncated_event_carries_lengths_only() -> None:
    event = input_truncated_event(3000, 2000)

    assert event.event == "input_truncated"
    assert json.loads(event.data) == {"original_length": 3000, "max_length": 2000}


def test_done_event_carries_the_turn_id() -> None:
    turn_id = uuid.uuid4()
    assert json.loads(done_event(turn_id).data) == {"turn_id": str(turn_id)}


def test_done_event_without_turn_id_is_empty() -> None:
    assert done_event().data == ""


def test_client_effect_event_payload() -> None:
    from app.models.client_effect import FiredEffect
    from app.turn.steps.response_streamer import client_effect_event

    effect = FiredEffect(
        kind="phone_echo", params={"record_ms": 6000, "delay_ms": 2500}
    )
    event = client_effect_event(effect)
    assert event.event == "client_effect"
    assert json.loads(event.data) == {
        "kind": "phone_echo",
        "params": {"record_ms": 6000, "delay_ms": 2500},
    }

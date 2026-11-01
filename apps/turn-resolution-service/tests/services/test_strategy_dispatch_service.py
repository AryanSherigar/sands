import asyncio
from uuid import uuid4

import httpx
import pytest
from app.integrations import openai_compatible_client
from app.services.strategy_dispatch_service import stream_dispatch
from strategy_contracts.agents import (
    AgentTrait,
    AgentView,
    DispatchBriefing,
    DispatchClaim,
    DispatchView,
)
from strategy_contracts.pressure import PressureBand, RumorTopic


def _view(status: str = "generating", narration: str | None = None) -> DispatchView:
    return DispatchView(
        rumor_id="rumor_1",
        turn=4,
        agent=AgentView(name="Aldous", traits=[AgentTrait.HONEST]),
        about_faction_id="house_dunwick",
        topic=RumorTopic.WILL,
        status=status,
        narration=narration,
        fallback_line_key="will.high",
    )


def _claim(status: str = "generating", narration: str | None = None) -> DispatchClaim:
    briefing = DispatchBriefing(
        rumor_id="rumor_1",
        playthrough_id=uuid4(),
        turn=4,
        agent=AgentView(name="Aldous", traits=[AgentTrait.HONEST]),
        about_faction_id="house_dunwick",
        topic=RumorTopic.WILL,
        reported_band=PressureBand.HIGH,
    )
    return DispatchClaim(
        dispatch=_view(status, narration),
        briefing=briefing,
        lease_token=uuid4(),
    )


class _Client:
    def __init__(self, fails_to_complete: bool = False) -> None:
        self.saved: list[str] = []
        self.failures: list[str] = []
        self.fails_to_complete = fails_to_complete

    async def complete(self, identity, rumor_id, request):
        if self.fails_to_complete:
            raise httpx.ConnectError("unavailable")
        self.saved.append(request.narration)

    async def fail(self, identity, rumor_id, request):
        self.failures.append(request.error_code)


class _Reservation:
    def __init__(self) -> None:
        self.refund_count = 0

    async def refund(self) -> None:
        self.refund_count += 1


def _narrator(monkeypatch, *chunks: str, error: Exception | None = None):
    async def stream(*args, **kwargs):
        for chunk in chunks:
            yield chunk
        if error is not None:
            raise error

    monkeypatch.setattr(openai_compatible_client, "stream_narration", stream)


async def test_success_saves_once_before_done(monkeypatch) -> None:
    client = _Client()
    _narrator(monkeypatch, "My lord, ", "all is calm.")

    events = [e async for e in stream_dispatch(_claim(), client, None)]

    assert client.saved == ["My lord, all is calm."]
    assert [e["event"] for e in events] == [
        "dispatch_started",
        "narration",
        "narration",
        "done",
    ]


async def test_prompt_given_to_the_model_hides_bribery(monkeypatch) -> None:
    seen: dict[str, str] = {}

    async def stream(system, prompt, *args, **kwargs):
        seen["text"] = (system + prompt).lower()
        yield "Calm."

    monkeypatch.setattr(openai_compatible_client, "stream_narration", stream)

    [e async for e in stream_dispatch(_claim(), _Client(), None)]

    assert "bribe" not in seen["text"] and "true" not in seen["text"]


async def test_completed_dispatch_replays_saved_text_without_the_model(
    monkeypatch,
) -> None:
    async def forbidden(*args, **kwargs):
        pytest.fail("saved dispatch must not call the model")
        yield ""

    monkeypatch.setattr(openai_compatible_client, "stream_narration", forbidden)

    events = [
        e
        async for e in stream_dispatch(
            _claim("completed", "Saved letter."), _Client(), None
        )
    ]

    assert [e["event"] for e in events] == ["dispatch_started", "narration", "done"]
    assert events[1]["data"] == "Saved letter."


async def test_model_failure_reports_fail_degrades_and_refunds(monkeypatch) -> None:
    client, reservation = _Client(), _Reservation()
    _narrator(monkeypatch, "Partial", error=TimeoutError())

    events = [e async for e in stream_dispatch(_claim(), client, reservation)]

    assert client.failures == ["provider_timeout"]
    assert events[-1]["event"] == "degraded"
    assert not any(e["event"] == "done" for e in events)
    assert reservation.refund_count == 1


async def test_failed_save_degrades_with_no_done(monkeypatch) -> None:
    client = _Client(fails_to_complete=True)
    _narrator(monkeypatch, "Letter.")

    events = [e async for e in stream_dispatch(_claim(), client, None)]

    assert events[-1]["event"] == "degraded"
    assert client.failures == ["provider_unavailable"]


async def test_cancel_before_output_refunds_and_records_failure(monkeypatch) -> None:
    client, reservation = _Client(), _Reservation()
    _narrator(monkeypatch, error=asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        [e async for e in stream_dispatch(_claim(), client, reservation)]

    assert client.failures == ["stream_cancelled"]
    assert reservation.refund_count == 1

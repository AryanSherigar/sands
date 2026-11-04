import asyncio
import json
from uuid import uuid4

import httpx
import pytest
from strategy_contracts.epilogue import (
    EpilogueBriefing,
    EpilogueClaim,
    EpilogueView,
)


def _claim(status: str = "generating", narration: str | None = None) -> EpilogueClaim:
    return EpilogueClaim(
        epilogue=EpilogueView(status=status, narration=narration),
        briefing=EpilogueBriefing(
            playthrough_id=uuid4(),
            chronicler_id="vaelen",
            ruler_name="Aldric",
            ending_id="default_defeat_capital_lost",
            ending_kind="defeat",
            ending_turn=2,
        ),
        input_hash="a" * 64,
        lease_token=uuid4(),
    )


class _Reservation:
    def __init__(self) -> None:
        self.refund_count = 0

    async def refund(self) -> None:
        self.refund_count += 1


class _Client:
    def __init__(self) -> None:
        self.saved: list[str] = []
        self.failures: list[str] = []

    async def complete(self, identity, request):
        self.saved.append(request.narration)

    async def fail(self, identity, request):
        self.failures.append(request.error_code)


async def test_stream_writes_in_the_fixed_chroniclers_voice_and_saves_before_done(
    monkeypatch,
) -> None:
    from app.integrations import narration_router
    from app.services.strategy_epilogue_service import stream_epilogue

    systems: list[str] = []

    async def narrator(system, prompt, *args, **kwargs):
        systems.append(system)
        yield "They remember "
        yield "the fall."

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    client = _Client()
    events = [event async for event in stream_epilogue(_claim(), client, None)]

    assert client.saved == ["They remember the fall."]
    assert "Vaelen the Scorned" in systems[0]
    assert [event["event"] for event in events] == [
        "epilogue_started",
        "narration",
        "narration",
        "done",
    ]
    assert json.loads(events[0]["data"])["chronicler_id"] == "vaelen"


async def test_completed_epilogue_replays_without_calling_the_model(
    monkeypatch,
) -> None:
    from app.integrations import narration_router
    from app.services.strategy_epilogue_service import stream_epilogue

    async def narrator(*args, **kwargs):
        pytest.fail("a saved epilogue must not call the model")
        yield ""

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    claim = _claim(status="completed", narration="Saved legacy.")
    events = [event async for event in stream_epilogue(claim, _Client(), None)]
    assert events[1] == {"event": "narration", "data": "Saved legacy."}
    assert events[-1]["event"] == "done"


async def test_provider_failure_records_the_failure_and_refunds_quota(
    monkeypatch,
) -> None:
    from app.integrations import narration_router
    from app.services.strategy_epilogue_service import stream_epilogue

    async def narrator(*args, **kwargs):
        raise TimeoutError
        yield ""

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    client, reservation = _Client(), _Reservation()
    events = [event async for event in stream_epilogue(_claim(), client, reservation)]
    assert events[-1]["event"] == "epilogue_error"
    assert client.failures == ["provider_timeout"]
    assert reservation.refund_count == 1
    assert not any(event["event"] == "done" for event in events)


async def test_save_failure_emits_an_error_and_no_done(monkeypatch) -> None:
    from app.integrations import narration_router
    from app.services.strategy_epilogue_service import stream_epilogue

    class FailingClient(_Client):
        async def complete(self, identity, request):
            raise httpx.ConnectError("unavailable")

    async def narrator(*args, **kwargs):
        yield "Provisional."

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    events = [event async for event in stream_epilogue(_claim(), FailingClient(), None)]
    assert events[-1]["event"] == "epilogue_error"
    assert not any(event["event"] == "done" for event in events)


async def test_cancel_before_any_output_refunds_quota(monkeypatch) -> None:
    from app.integrations import narration_router
    from app.services.strategy_epilogue_service import stream_epilogue

    async def narrator(*args, **kwargs):
        raise asyncio.CancelledError
        yield ""

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    client, reservation = _Client(), _Reservation()
    with pytest.raises(asyncio.CancelledError):
        async for _ in stream_epilogue(_claim(), client, reservation):
            pass
    assert reservation.refund_count == 1
    assert client.failures == ["stream_cancelled"]

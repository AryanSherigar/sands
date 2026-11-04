from uuid import uuid4

import pytest
from strategy_contracts.summary import (
    SummaryBriefing,
    SummaryClaim,
    SummaryFact,
    SummaryView,
)


def _claim(chronicler_id: str = "lucan"):
    summary = uuid4()
    return SummaryClaim(
        summary=SummaryView(
            summary_id=summary,
            requested_turn=0,
            trigger="major_event",
            status="generating",
        ),
        briefing=SummaryBriefing(
            summary_id=summary,
            playthrough_id=uuid4(),
            observer_faction_id="player",
            chronicler_id=chronicler_id,
            requested_turn=0,
            trigger="major_event",
            facts=[
                SummaryFact(
                    event_id=uuid4(),
                    kind="uprising_started",
                    turn=0,
                    text_key="uprising_started",
                )
            ],
        ),
        input_hash="a" * 64,
        lease_token=uuid4(),
    )


async def test_summary_stream_saves_before_done_and_never_mutates_game(monkeypatch):
    from app.integrations import narration_router
    from app.services.strategy_summary_service import stream_summary

    saved = []

    class Client:
        async def complete(self, identity, summary_id, request):
            saved.append(request.narration)

        async def fail(self, identity, summary_id, request):
            pytest.fail("successful generation must not fail")

    async def narrator(*args, **kwargs):
        yield "The realm "
        yield "stirs."

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    events = [event async for event in stream_summary(_claim(), Client(), None)]
    assert saved == ["The realm stirs."]
    assert [event["event"] for event in events] == [
        "summary_started",
        "narration",
        "narration",
        "done",
    ]


async def test_summary_stream_with_chronicler_persona_applies_system_prompt(
    monkeypatch,
):
    import json

    from app.integrations import narration_router
    from app.services.strategy_summary_service import stream_summary

    recorded_prompts = []

    class Client:
        async def complete(self, identity, summary_id, request):
            pass

        async def fail(self, identity, summary_id, request):
            pass

    async def narrator(system_prompt, prompt, *args, **kwargs):
        recorded_prompts.append((system_prompt, prompt))
        yield "By the King's right..."

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    events = [
        event async for event in stream_summary(_claim("morvath"), Client(), None)
    ]

    assert len(recorded_prompts) == 1
    system_prompt, _ = recorded_prompts[0]
    assert "Morvath of Highcourt" in system_prompt
    assert "Crown Loyalist" in system_prompt

    started_data = json.loads(events[0]["data"])
    assert started_data["chronicler_id"] == "morvath"
    assert started_data["chronicler_name"] == "Morvath of Highcourt"


async def test_summary_stream_uses_brother_lucan_for_a_default_briefing(monkeypatch):
    import json

    from app.integrations import narration_router
    from app.services.strategy_summary_service import stream_summary

    recorded_prompts = []

    class Client:
        async def complete(self, identity, summary_id, request):
            pass

        async def fail(self, identity, summary_id, request):
            pass

    async def narrator(system_prompt, prompt, *args, **kwargs):
        recorded_prompts.append((system_prompt, prompt))
        yield "A solemn record..."

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    events = [event async for event in stream_summary(_claim(), Client(), None)]

    assert len(recorded_prompts) == 1
    system_prompt, _ = recorded_prompts[0]
    assert "Brother Lucan" in system_prompt

    started_data = json.loads(events[0]["data"])
    assert started_data["chronicler_id"] == "lucan"
    assert started_data["chronicler_name"] == "Brother Lucan"


async def test_failed_completion_emits_error_and_no_done(monkeypatch):
    import httpx
    from app.integrations import narration_router
    from app.services.strategy_summary_service import stream_summary

    class Client:
        async def complete(self, identity, summary_id, request):
            raise httpx.ConnectError("unavailable")

        async def fail(self, identity, summary_id, request):
            return None

    async def narrator(*args, **kwargs):
        yield "Provisional."

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    events = [event async for event in stream_summary(_claim(), Client(), None)]
    assert events[-1]["event"] == "summary_error"
    assert not any(event["event"] == "done" for event in events)


async def test_completed_claim_replays_saved_prose_without_provider():
    from app.services.strategy_summary_service import stream_summary

    class Client:
        async def complete(self, identity, summary_id, request):
            pytest.fail("saved chronicle must not complete again")

        async def fail(self, identity, summary_id, request):
            pytest.fail("saved chronicle must not fail")

    pending = _claim()
    claim = pending.model_copy(
        update={
            "summary": pending.summary.model_copy(
                update={"status": "completed", "narration": "Saved prose."}
            )
        }
    )
    events = [event async for event in stream_summary(claim, Client(), None)]
    assert [event["event"] for event in events] == [
        "summary_started",
        "narration",
        "done",
    ]
    assert events[1]["data"] == "Saved prose."


class _Reservation:
    def __init__(self):
        self.refund_count = 0

    async def refund(self):
        self.refund_count += 1


async def _cancel_after(monkeypatch, chunks):
    import asyncio

    from app.integrations import narration_router
    from app.services.strategy_summary_service import stream_summary

    class Client:
        async def complete(self, identity, summary_id, request):
            pytest.fail("cancelled generation must not complete")

        async def fail(self, identity, summary_id, request):
            return None

    async def narrator(*args, **kwargs):
        for chunk in chunks:
            yield chunk
        raise asyncio.CancelledError

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    reservation = _Reservation()
    with pytest.raises(asyncio.CancelledError):
        async for _ in stream_summary(_claim(), Client(), reservation):
            pass
    return reservation


async def test_cancel_after_streamed_output_keeps_quota_charged(monkeypatch):
    reservation = await _cancel_after(monkeypatch, ["The realm "])
    assert reservation.refund_count == 0


async def test_cancel_before_any_output_refunds_quota(monkeypatch):
    reservation = await _cancel_after(monkeypatch, [])
    assert reservation.refund_count == 1


def test_chronicle_rules_forbid_narrating_the_limits_of_the_record() -> None:
    from app.services.chronicler_personas import BASE_CHRONICLE_RULES

    assert "never comment on the limits of your records" in BASE_CHRONICLE_RULES
    assert "Do not invent causes" in BASE_CHRONICLE_RULES

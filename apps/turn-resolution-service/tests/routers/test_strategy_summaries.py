import json
from uuid import uuid4

import httpx
import respx
from app.config import settings
from strategy_contracts.summary import (
    SummaryBriefing,
    SummaryClaim,
    SummaryFact,
    SummaryView,
)


def _claim() -> SummaryClaim:
    summary_id = uuid4()
    return SummaryClaim(
        summary=SummaryView(
            summary_id=summary_id,
            requested_turn=3,
            trigger="major_event",
            status="generating",
        ),
        briefing=SummaryBriefing(
            summary_id=summary_id,
            playthrough_id=uuid4(),
            observer_faction_id="player",
            requested_turn=3,
            trigger="major_event",
            facts=[
                SummaryFact(
                    event_id=uuid4(),
                    kind="uprising_started",
                    turn=3,
                    text_key="uprising_started",
                    region_ids=["home"],
                )
            ],
        ),
        input_hash="a" * 64,
        lease_token=uuid4(),
    )


@respx.mock
async def test_stream_claims_then_saves_before_done(async_client, monkeypatch) -> None:
    from app.integrations import narration_router

    claim = _claim()
    user = uuid4()
    monkeypatch.setattr(settings, "simulation_url", "http://simulation.test")
    monkeypatch.setattr(settings, "internal_service_token", "service-token")

    async def narrator(
        system: str, prompt: str, timeout_seconds: int, **kwargs: object
    ):
        assert timeout_seconds == 60
        assert "observed event facts only" in system.lower()
        assert '"kind": "uprising_started"' in prompt
        yield "The realm stirs."

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    identity = claim.briefing.playthrough_id
    base = f"http://simulation.test/v1/playthroughs/{identity}/summaries/{claim.summary.summary_id}"
    pending = claim.summary.model_copy(update={"status": "pending"})
    respx.get(base).mock(
        return_value=httpx.Response(200, json=pending.model_dump(mode="json"))
    )
    claimed = respx.post(base.replace("/v1/", "/internal/v1/") + "/claim").mock(
        return_value=httpx.Response(200, json=claim.model_dump(mode="json"))
    )
    completed = claim.summary.model_copy(
        update={"status": "completed", "narration": "The realm stirs."}
    )
    saved = respx.post(base.replace("/v1/", "/internal/v1/") + "/complete").mock(
        return_value=httpx.Response(200, json=completed.model_dump(mode="json"))
    )

    client_request_id = uuid4()
    response = await async_client.post(
        f"/v1/strategy/playthroughs/{identity}/summaries/{claim.summary.summary_id}/stream",
        json={"client_request_id": str(client_request_id)},
        headers={"X-Dev-User-Id": str(user)},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: summary_started" in response.text
    assert "event: narration" in response.text
    assert "event: done" in response.text
    assert claimed.called and saved.called
    assert json.loads(claimed.calls[0].request.content)["claim_id"] == str(
        client_request_id
    )
    assert saved.calls[0].request.headers["x-internal-service-token"] == "service-token"
    assert saved.calls[0].request.headers["x-dev-user-id"] == str(user)

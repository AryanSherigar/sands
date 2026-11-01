import json
from uuid import uuid4

import httpx
import respx
from app.config import settings
from app.integrations import openai_compatible_client
from strategy_contracts.agents import (
    AgentTrait,
    AgentView,
    DispatchBriefing,
    DispatchClaim,
    DispatchView,
)
from strategy_contracts.pressure import PressureBand, RumorTopic


def _view(status: str, narration: str | None = None) -> DispatchView:
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


def _claim(identity) -> DispatchClaim:
    return DispatchClaim(
        dispatch=_view("generating"),
        briefing=DispatchBriefing(
            rumor_id="rumor_1",
            playthrough_id=identity,
            turn=4,
            agent=AgentView(name="Aldous", traits=[AgentTrait.HONEST]),
            about_faction_id="house_dunwick",
            topic=RumorTopic.WILL,
            reported_band=PressureBand.HIGH,
        ),
        lease_token=uuid4(),
    )


@respx.mock
async def test_stream_claims_saves_then_done(async_client, monkeypatch) -> None:
    identity, user = uuid4(), uuid4()
    monkeypatch.setattr(settings, "simulation_url", "http://simulation.test")
    monkeypatch.setattr(settings, "internal_service_token", "service-token")

    async def narrator(system: str, prompt: str, timeout_seconds: int, **kwargs):
        yield "All is calm."

    monkeypatch.setattr(openai_compatible_client, "stream_narration", narrator)
    base = f"http://simulation.test/v1/playthroughs/{identity}/dispatches/rumor_1"
    respx.get(base).mock(
        return_value=httpx.Response(200, json=_view("pending").model_dump(mode="json"))
    )
    claimed = respx.post(base.replace("/v1/", "/internal/v1/") + "/claim").mock(
        return_value=httpx.Response(200, json=_claim(identity).model_dump(mode="json"))
    )
    saved = respx.post(base.replace("/v1/", "/internal/v1/") + "/complete").mock(
        return_value=httpx.Response(
            200, json=_view("completed", "All is calm.").model_dump(mode="json")
        )
    )
    request_id = uuid4()

    response = await async_client.post(
        f"/v1/strategy/playthroughs/{identity}/dispatches/rumor_1/stream",
        json={"client_request_id": str(request_id)},
        headers={"X-Dev-User-Id": str(user)},
    )

    assert response.status_code == 200
    assert "event: dispatch_started" in response.text
    assert "event: narration" in response.text
    assert "event: done" in response.text
    assert json.loads(claimed.calls[0].request.content)["claim_id"] == str(request_id)
    assert json.loads(saved.calls[0].request.content)["narration"] == "All is calm."


@respx.mock
async def test_unknown_playthrough_is_not_streamed(async_client, monkeypatch) -> None:
    identity = uuid4()
    monkeypatch.setattr(settings, "simulation_url", "http://simulation.test")
    respx.get(
        f"http://simulation.test/v1/playthroughs/{identity}/dispatches/rumor_9"
    ).mock(return_value=httpx.Response(404, json={"detail": "nope"}))

    response = await async_client.post(
        f"/v1/strategy/playthroughs/{identity}/dispatches/rumor_9/stream",
        json={"client_request_id": str(uuid4())},
        headers={"X-Dev-User-Id": str(uuid4())},
    )

    assert response.status_code == 404

import json
from uuid import uuid4

import httpx
import respx
from app.config import settings
from strategy_contracts.epilogue import EpilogueBriefing, EpilogueClaim, EpilogueView


def _claim() -> EpilogueClaim:
    return EpilogueClaim(
        epilogue=EpilogueView(status="generating"),
        briefing=EpilogueBriefing(
            playthrough_id=uuid4(),
            chronicler_id="morvath",
            ruler_name="Aldric",
            ending_id="default_victory_conquest",
            ending_kind="victory",
            grade=None,
            ending_turn=20,
        ),
        input_hash="b" * 64,
        lease_token=uuid4(),
    )


@respx.mock
async def test_stream_claims_then_saves_the_closing_entry_before_done(
    async_client, monkeypatch
) -> None:
    from app.integrations import narration_router

    claim = _claim()
    identity = claim.briefing.playthrough_id
    monkeypatch.setattr(settings, "simulation_url", "http://simulation.test")
    monkeypatch.setattr(settings, "internal_service_token", "service-token")

    async def narrator(system, prompt, timeout_seconds, **kwargs):
        assert "Morvath of Highcourt" in system
        yield "The crown endured."

    monkeypatch.setattr(narration_router, "stream_narration", narrator)
    base = f"http://simulation.test/v1/playthroughs/{identity}/epilogue"
    internal = base.replace("/v1/", "/internal/v1/")
    pending = EpilogueView(status="pending")
    respx.get(base).mock(
        return_value=httpx.Response(200, json=pending.model_dump(mode="json"))
    )
    claimed = respx.post(internal + "/claim").mock(
        return_value=httpx.Response(200, json=claim.model_dump(mode="json"))
    )
    done = EpilogueView(status="completed", narration="The crown endured.")
    saved = respx.post(internal + "/complete").mock(
        return_value=httpx.Response(200, json=done.model_dump(mode="json"))
    )

    request_id = uuid4()
    response = await async_client.post(
        f"/v1/strategy/playthroughs/{identity}/epilogue/stream",
        json={"client_request_id": str(request_id)},
        headers={"X-Dev-User-Id": str(uuid4())},
    )

    assert response.status_code == 200
    assert "event: epilogue_started" in response.text
    assert "event: done" in response.text
    assert claimed.called and saved.called
    assert json.loads(claimed.calls[0].request.content)["claim_id"] == str(request_id)
    assert saved.calls[0].request.headers["x-internal-service-token"] == "service-token"


@respx.mock
async def test_stream_replays_a_saved_epilogue_without_claiming(
    async_client, monkeypatch
) -> None:
    identity = uuid4()
    monkeypatch.setattr(settings, "simulation_url", "http://simulation.test")
    monkeypatch.setattr(settings, "internal_service_token", "service-token")
    base = f"http://simulation.test/v1/playthroughs/{identity}/epilogue"
    saved = EpilogueView(status="completed", narration="Saved legacy.")
    respx.get(base).mock(
        return_value=httpx.Response(200, json=saved.model_dump(mode="json"))
    )
    claim_route = respx.post(base.replace("/v1/", "/internal/v1/") + "/claim")

    response = await async_client.post(
        f"/v1/strategy/playthroughs/{identity}/epilogue/stream",
        json={"client_request_id": str(uuid4())},
        headers={"X-Dev-User-Id": str(uuid4())},
    )

    assert response.status_code == 200
    assert "Saved legacy." in response.text
    assert not claim_route.called

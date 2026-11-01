from uuid import uuid4

import httpx
import respx
from app.config import settings
from strategy_contracts.art import ArtBriefing, ArtClaim, ArtView

ART_URL = "https://cdn.test/strategy-art/one.webp"


def _claim(status: str = "generating") -> ArtClaim:
    return ArtClaim(
        art=ArtView(kind="event", item_id="evt_1", status=status, art_url=None),
        briefing=ArtBriefing(kind="event", item_id="evt_1", headline="Tax Grievance"),
        lease_token=uuid4(),
    )


def _body() -> dict[str, str]:
    return {"kind": "event", "item_id": "evt_1", "client_request_id": str(uuid4())}


async def test_requires_auth(async_client) -> None:
    response = await async_client.post(
        f"/v1/strategy/playthroughs/{uuid4()}/art", json=_body()
    )
    assert response.status_code in (401, 403)


async def test_unknown_kind_is_422(async_client) -> None:
    body = {**_body(), "kind": "battle"}
    response = await async_client.post(
        f"/v1/strategy/playthroughs/{uuid4()}/art",
        json=body,
        headers={"X-Dev-User-Id": str(uuid4())},
    )
    assert response.status_code == 422


@respx.mock
async def test_returns_art_view(async_client, monkeypatch) -> None:
    from app.turn.steps import strategy_art_generator

    monkeypatch.setattr(settings, "simulation_url", "http://simulation.test")
    monkeypatch.setattr(settings, "internal_service_token", "service-token")

    async def generator(briefing, timeout):
        return ART_URL

    monkeypatch.setattr(strategy_art_generator, "generate_strategy_art", generator)
    from app.services import strategy_art_service

    monkeypatch.setattr(strategy_art_service, "generate_strategy_art", generator)
    identity = uuid4()
    base = f"http://simulation.test/internal/v1/playthroughs/{identity}/art/event/evt_1"
    claim = _claim()
    respx.post(f"{base}/claim").mock(
        return_value=httpx.Response(200, json=claim.model_dump(mode="json"))
    )
    done = claim.art.model_copy(update={"status": "completed", "art_url": ART_URL})
    respx.post(f"{base}/complete").mock(
        return_value=httpx.Response(200, json=done.model_dump(mode="json"))
    )
    response = await async_client.post(
        f"/v1/strategy/playthroughs/{identity}/art",
        json=_body(),
        headers={"X-Dev-User-Id": str(uuid4())},
    )
    assert response.status_code == 200
    assert response.json()["art_url"] == ART_URL


async def test_item_id_with_path_characters_is_rejected(async_client) -> None:
    body = {**_body(), "item_id": "../../../internal/v1/x"}
    response = await async_client.post(
        f"/v1/strategy/playthroughs/{uuid4()}/art",
        json=body,
        headers={"X-Dev-User-Id": str(uuid4())},
    )
    assert response.status_code == 422

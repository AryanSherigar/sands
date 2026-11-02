from uuid import UUID

import respx
from app.config import get_settings
from httpx import AsyncClient
from tests.routers.test_order_api import PLAYER_FACTION, RAISE_TAX, guard
from tests.services.helpers import mutation
from tests.services.test_campaign_service_endings import (
    _request_with_foreign_player_capital,
)

HEADERS = {"X-Internal-Service-Token": "internal"}


async def _start_ended_game(api: AsyncClient) -> str:
    request = _request_with_foreign_player_capital().model_dump(mode="json")
    await api.post("/internal/v1/playthroughs", json=request, headers=HEADERS)
    playthrough_id = request["playthrough_id"]
    sync_url = (
        f"{get_settings().core_api_url}/internal/v1/playthroughs/{playthrough_id}/turn"
    )
    respx.patch(sync_url).respond(
        status_code=200,
        json={"playthrough_id": playthrough_id, "turn_count": 1, "status": "active"},
    )
    base = f"/v1/playthroughs/{UUID(playthrough_id)}"
    ended = await api.post(f"{base}/end-turn", json=mutation("begin", 1).model_dump())
    assert ended.status_code == 200
    return base


@respx.mock
async def test_world_view_shows_the_ending_without_scores(api: AsyncClient) -> None:
    base = await _start_ended_game(api)
    ending = (await api.get(f"{base}/world")).json()["ending"]
    assert ending["ending_id"] == "default_defeat_capital_lost"
    assert "inputs" not in ending


@respx.mock
async def test_end_turn_after_the_ending_is_refused(api: AsyncClient) -> None:
    base = await _start_ended_game(api)
    second = mutation("again", 2, turn=1).model_dump()
    response = await api.post(f"{base}/end-turn", json=second)
    assert response.status_code == 409
    assert "game_ended" in response.text


@respx.mock
async def test_an_order_after_the_ending_is_refused(api: AsyncClient) -> None:
    base = await _start_ended_game(api)
    version = (await api.get(f"{base}/world")).json()["world_version"]
    body = guard("tax", version) | {"command": RAISE_TAX, "expected_turn": 1}
    response = await api.post(f"{base}/commands", json=body)
    assert response.status_code == 409
    assert "game_ended" in response.text
    assert PLAYER_FACTION

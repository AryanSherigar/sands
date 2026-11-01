from uuid import uuid4

from httpx import AsyncClient
from tests.services.helpers import mutation
from tests.services.test_campaign_service import initialization

HEADERS = {"X-Internal-Service-Token": "internal"}


async def _complete_first_turn(api: AsyncClient) -> str:
    request = initialization().model_dump(mode="json")
    initial = await api.post("/internal/v1/playthroughs", json=request, headers=HEADERS)
    base = f"/v1/playthroughs/{request['playthrough_id']}"
    command = {
        "operation_id": "tax",
        "expected_world_version": initial.json()["world_version"],
        "expected_turn": 0,
        "expected_wave": 0,
        "command": {
            "kind": "set_tax_rate",
            "faction_id": "house_carrow",
            "tax_rate": "high",
        },
    }
    accepted = await api.post(f"{base}/commands", json=command)
    ended = await api.post(
        f"{base}/end-turn",
        json=mutation("begin", accepted.json()["world_version"]).model_dump(),
    )
    assert ended.json()["status"] == "turn_completed"
    return base


async def test_report_lists_the_gold_flows_of_the_completed_turn(
    api: AsyncClient,
) -> None:
    base = await _complete_first_turn(api)
    response = await api.get(f"{base}/turns/0/report")
    assert response.status_code == 200
    body = response.json()
    categories = {line["category"] for line in body["economy"]}
    assert "tax" in categories
    assert body["net_gold"] == sum(line["amount"] for line in body["economy"])
    assert any(line["kind"] == "tax_rate_set" for line in body["lines"])


async def test_report_for_a_turn_with_no_events_is_empty(api: AsyncClient) -> None:
    base = await _complete_first_turn(api)
    body = (await api.get(f"{base}/turns/9/report")).json()
    assert body["economy"] == [] and body["battles"] == [] and body["lines"] == []


async def test_report_requires_an_owned_playthrough(api: AsyncClient) -> None:
    assert (
        await api.get(f"/v1/playthroughs/{uuid4()}/turns/0/report")
    ).status_code == 404

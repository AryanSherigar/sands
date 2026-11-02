import pytest
from httpx import AsyncClient
from tests.services.test_campaign_service import initialization

INTERNAL = {"X-Internal-Service-Token": "internal"}


async def _start(api: AsyncClient) -> str:
    request = initialization().model_dump(mode="json")
    created = await api.post(
        "/internal/v1/playthroughs", json=request, headers=INTERNAL
    )
    assert created.status_code == 200
    return f"/v1/playthroughs/{request['playthrough_id']}"


@pytest.mark.asyncio
async def test_convene_proclamation_council(api: AsyncClient) -> None:
    base = await _start(api)
    payload = {
        "draft": {
            "is_recognized": True,
            "domain": "martial_levies",
            "burden": "moderate",
            "legal_summary": "Draft 150 spearmen from the capital.",
        },
        "is_rescinding_previous": False,
    }
    resp = await api.post(f"{base}/proclamation/convene", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["ministers"]) == 4
    assert data["draft"]["domain"] == "martial_levies"
    assert data["exchange_cap"] == 6


@pytest.mark.asyncio
async def test_decide_proclamation_and_rescission(api: AsyncClient) -> None:
    base = await _start(api)
    payload = {
        "draft": {
            "is_recognized": True,
            "domain": "emergency_taxation",
            "burden": "moderate",
            "legal_summary": "Levy 200 silver from guild halls.",
        },
        "verdict": "fiat",
        "is_rescinding_previous": False,
    }
    decide_resp = await api.post(f"{base}/proclamation/decision", json=payload)
    assert decide_resp.status_code == 200
    data = decide_resp.json()
    assert data["domain"] == "emergency_taxation"
    assert data["remaining_turns"] == 4

    # Convening without rescinding flag must fail with 400
    convene_fail = await api.post(
        f"{base}/proclamation/convene",
        json={
            "draft": {
                "is_recognized": True,
                "domain": "martial_levies",
                "burden": "light",
                "legal_summary": "New levy.",
            },
            "is_rescinding_previous": False,
        },
    )
    assert convene_fail.status_code == 400
    assert "active proclamation is already in effect" in convene_fail.json()["detail"]

    # Convening with rescinding flag succeeds
    convene_ok = await api.post(
        f"{base}/proclamation/convene",
        json={
            "draft": {
                "is_recognized": True,
                "domain": "martial_levies",
                "burden": "light",
                "legal_summary": "New levy.",
            },
            "is_rescinding_previous": True,
        },
    )
    assert convene_ok.status_code == 200

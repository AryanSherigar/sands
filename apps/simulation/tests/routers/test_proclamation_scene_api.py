import pytest
from httpx import AsyncClient
from tests.services.helpers import mutation
from tests.services.test_campaign_service import initialization

INTERNAL = {"X-Internal-Service-Token": "internal"}


async def _start(api: AsyncClient) -> str:
    request = initialization().model_dump(mode="json")
    created = await api.post(
        "/internal/v1/playthroughs", json=request, headers=INTERNAL
    )
    assert created.status_code == 200
    return f"/v1/playthroughs/{request['playthrough_id']}"


async def _guard(api: AsyncClient, base: str, operation_id: str) -> dict:
    world = (await api.get(f"{base}/world")).json()
    return mutation(operation_id, world["world_version"], world["turn"]).model_dump()


TAX_DRAFT = {
    "is_recognized": True,
    "domain": "emergency_taxation",
    "burden": "moderate",
    "legal_summary": "Levy 200 silver from guild halls.",
}


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
    payload["guard"] = await _guard(api, base, "decide-1")
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


@pytest.mark.asyncio
async def test_a_decided_proclamation_survives_replay_verification(
    api: AsyncClient,
) -> None:
    base = await _start(api)
    decided = await api.post(
        f"{base}/proclamation/decision",
        json={"guard": await _guard(api, base, "decide-1"), "draft": TAX_DRAFT},
    )
    assert decided.status_code == 200
    world = (await api.get(f"{base}/world")).json()
    ended = await api.post(
        f"{base}/end-turn", json=mutation("end-1", world["world_version"]).model_dump()
    )
    assert ended.status_code == 200

    verified = await api.post(f"{base}/replay/verify")

    assert verified.status_code == 200, verified.text
    assert verified.json()["step_count"] >= 2


@pytest.mark.asyncio
async def test_retrying_a_decision_does_not_charge_the_mandates_twice(
    api: AsyncClient,
) -> None:
    base = await _start(api)
    body = {"guard": await _guard(api, base, "decide-1"), "draft": TAX_DRAFT}
    mandates_before = (await api.get(f"{base}/world")).json()["orders_remaining"]

    first = await api.post(f"{base}/proclamation/decision", json=body)
    retry = await api.post(f"{base}/proclamation/decision", json=body)

    assert first.status_code == retry.status_code == 200
    mandates_after = (await api.get(f"{base}/world")).json()["orders_remaining"]
    assert mandates_before - mandates_after == 2


@pytest.mark.asyncio
async def test_an_unrecognized_proclamation_cannot_be_enacted(
    api: AsyncClient,
) -> None:
    base = await _start(api)
    draft = {"is_recognized": False, "legal_summary": "Unintelligible."}

    response = await api.post(
        f"{base}/proclamation/decision",
        json={"guard": await _guard(api, base, "decide-1"), "draft": draft},
    )

    assert response.status_code == 422
    assert "not understood" in response.json()["detail"]


@pytest.mark.asyncio
async def test_an_unknown_verdict_is_refused(api: AsyncClient) -> None:
    base = await _start(api)

    response = await api.post(
        f"{base}/proclamation/decision",
        json={
            "guard": await _guard(api, base, "decide-1"),
            "draft": TAX_DRAFT,
            "verdict": "tyranny",
        },
    )

    assert response.status_code == 422

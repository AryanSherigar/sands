"""Integration tests for the rule check REST endpoints."""

import uuid

import httpx
import pytest
from app.repositories.user_repo import UserRepo
from sqlalchemy.ext.asyncio import AsyncSession

STATE_SCHEMA = {
    "clock": {"type": "number", "initial": 0},
    "rule_r3": {
        "type": "enum",
        "options": ["answered", "ignored", "unseen"],
        "initial": "unseen",
    },
}


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )


@pytest.fixture
def headers(dev_user):
    return {"x-dev-user-id": str(dev_user.user_id)}


@pytest.fixture
async def scenario_id(async_client: httpx.AsyncClient, headers) -> str:
    created = await async_client.post(
        "/v1/scenarios",
        json={"title": "Night Desk", "mode": "master", "complexity_tier": "master"},
        headers=headers,
    )
    scenario_id = created.json()["scenario_id"]
    await async_client.patch(
        f"/v1/scenarios/{scenario_id}",
        json={"state_schema": STATE_SCHEMA},
        headers=headers,
    )
    return scenario_id


async def _enable_rule_checks(async_client, headers, scenario_id: str) -> None:
    await async_client.put(
        f"/v1/scenarios/{scenario_id}/tools",
        json={"enabled_tools": ["rule_checks"]},
        headers=headers,
    )


def _payload(**overrides) -> dict[str, object]:
    payload: dict[str, object] = {
        "label": "03:14 phone",
        "kind": "timed_choice",
        "trigger_condition_expression": {"field": "clock", "op": ">=", "value": 5},
        "result_path": "rule_r3",
        "params": {
            "prompt": "The phone rings.",
            "options": [
                {"id": "answer", "label": "Answer", "result": "answered"},
                {"id": "ignore", "label": "Ignore", "result": "ignored"},
            ],
            "window_ms": 12000,
            "timeout_result": "ignored",
        },
    }
    payload.update(overrides)
    return payload


async def test_create_while_tool_is_off_is_409_with_machine_code(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    response = await async_client.post(
        f"/v1/scenarios/{scenario_id}/rule-checks", json=_payload(), headers=headers
    )

    assert response.status_code == 409
    assert response.json()["code"] == "tool_not_enabled"
    assert "rule_checks" in response.json()["detail"]


async def test_create_list_get_update_delete_round_trip(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    await _enable_rule_checks(async_client, headers, scenario_id)
    base = f"/v1/scenarios/{scenario_id}/rule-checks"

    created = await async_client.post(base, json=_payload(), headers=headers)
    check_id = created.json()["check_id"]
    listed = await async_client.get(base, headers=headers)
    fetched = await async_client.get(f"{base}/{check_id}", headers=headers)
    patched = await async_client.patch(
        f"{base}/{check_id}", json={"label": "renamed"}, headers=headers
    )
    deleted = await async_client.delete(f"{base}/{check_id}", headers=headers)

    assert created.status_code == 201
    assert [c["check_id"] for c in listed.json()["items"]] == [check_id]
    assert fetched.json()["result_path"] == "rule_r3"
    assert patched.json()["label"] == "renamed"
    assert deleted.status_code == 204


async def test_invalid_params_are_422(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    await _enable_rule_checks(async_client, headers, scenario_id)
    bad = _payload()
    bad["params"]["window_ms"] = 10

    response = await async_client.post(
        f"/v1/scenarios/{scenario_id}/rule-checks", json=bad, headers=headers
    )

    assert response.status_code == 422


async def test_result_outside_the_enum_is_422(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    await _enable_rule_checks(async_client, headers, scenario_id)
    bad = _payload()
    bad["params"]["timeout_result"] = "fled"

    response = await async_client.post(
        f"/v1/scenarios/{scenario_id}/rule-checks", json=bad, headers=headers
    )

    assert response.status_code == 422


async def test_reorder_returns_the_new_order(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    await _enable_rule_checks(async_client, headers, scenario_id)
    base = f"/v1/scenarios/{scenario_id}/rule-checks"
    first = await async_client.post(
        base, json=_payload(label="A", priority=0), headers=headers
    )
    second = await async_client.post(
        base, json=_payload(label="B", priority=1), headers=headers
    )

    response = await async_client.post(
        f"{base}/reorder",
        json={
            "ordered_check_ids": [second.json()["check_id"], first.json()["check_id"]]
        },
        headers=headers,
    )

    assert [c["label"] for c in response.json()["items"]] == ["B", "A"]


async def test_another_user_cannot_list_checks(
    async_client: httpx.AsyncClient,
    db_session: AsyncSession,
    scenario_id: str,
):
    stranger = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Stranger"
    )

    response = await async_client.get(
        f"/v1/scenarios/{scenario_id}/rule-checks",
        headers={"x-dev-user-id": str(stranger.user_id)},
    )

    assert response.status_code in (403, 404)


async def test_scenario_duplicate_endpoint_keeps_tool_and_checks(
    async_client: httpx.AsyncClient, headers, scenario_id: str
):
    await _enable_rule_checks(async_client, headers, scenario_id)
    await async_client.post(
        f"/v1/scenarios/{scenario_id}/rule-checks", json=_payload(), headers=headers
    )

    copy = await async_client.post(
        f"/v1/scenarios/{scenario_id}/duplicate", headers=headers
    )
    copied = await async_client.get(
        f"/v1/scenarios/{copy.json()['scenario_id']}/rule-checks", headers=headers
    )

    assert copy.json()["enabled_tools"] == ["rule_checks"]
    assert len(copied.json()["items"]) == 1

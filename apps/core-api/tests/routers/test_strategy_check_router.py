"""Integration tests for the strategy publish-check endpoint."""

import json
import uuid
from pathlib import Path

import pytest
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from strategy_contracts.scenario import StrategyScenario

TRACED_MAP_PATH = (
    Path(__file__).parents[4]
    / "packages"
    / "strategy-contracts"
    / "tests"
    / "traced_map.json"
)


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )


@pytest.fixture
def headers(dev_user):
    return {"x-dev-user-id": str(dev_user.user_id)}


def _document_fields(mode: str) -> dict[str, object]:
    if mode != "strategy":
        return {}
    return {"strategy_document": StrategyScenario().model_dump(mode="json")}


async def _create_scenario(async_client: AsyncClient, headers, mode: str) -> str:
    response = await async_client.post(
        "/v1/scenarios",
        json={"title": "The Reach", "mode": mode, **_document_fields(mode)},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["scenario_id"]


def _check_path(scenario_id: str) -> str:
    return f"/v1/scenarios/{scenario_id}/strategy-check"


@pytest.mark.asyncio
async def test_check_reports_blockers_for_an_empty_draft(
    async_client: AsyncClient, headers
):
    scenario_id = await _create_scenario(async_client, headers, "strategy")

    response = await async_client.post(_check_path(scenario_id), headers=headers)

    assert response.status_code == 200
    codes = {issue["code"] for issue in response.json()["blocking"]}
    assert "no_playable_faction" in codes


@pytest.mark.asyncio
async def test_check_sees_a_map_saved_through_the_map_endpoint(
    async_client: AsyncClient, headers
):
    scenario_id = await _create_scenario(async_client, headers, "strategy")
    traced_map = json.loads(TRACED_MAP_PATH.read_text())
    await async_client.put(
        f"/v1/scenarios/{scenario_id}/strategy-map", json=traced_map, headers=headers
    )

    response = await async_client.post(_check_path(scenario_id), headers=headers)

    codes = {issue["code"] for issue in response.json()["blocking"]}
    assert "map_disconnected" not in codes
    assert "few_regions" in {issue["code"] for issue in response.json()["warnings"]}


@pytest.mark.asyncio
async def test_check_rejects_a_non_strategy_scenario(
    async_client: AsyncClient, headers
):
    scenario_id = await _create_scenario(async_client, headers, "newbie")

    response = await async_client.post(_check_path(scenario_id), headers=headers)

    assert response.status_code == 422

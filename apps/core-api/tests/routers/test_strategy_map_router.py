"""Integration tests for the strategy-mode region map endpoints."""

import copy
import json
import uuid
from pathlib import Path

import pytest
from app.integrations import storage_client
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
def traced_map() -> dict[str, object]:
    return json.loads(TRACED_MAP_PATH.read_text())


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )


@pytest.fixture
async def other_user(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Other Creator"
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


@pytest.fixture
async def strategy_scenario_id(async_client: AsyncClient, headers) -> str:
    return await _create_scenario(async_client, headers, "strategy")


def _path(scenario_id: str) -> str:
    return f"/v1/scenarios/{scenario_id}/strategy-map"


@pytest.mark.asyncio
async def test_save_then_get_round_trips_the_map(
    async_client: AsyncClient, headers, strategy_scenario_id, traced_map
):
    saved = await async_client.put(
        _path(strategy_scenario_id), json=traced_map, headers=headers
    )
    loaded = await async_client.get(_path(strategy_scenario_id), headers=headers)

    assert saved.status_code == 200
    assert saved.json() == traced_map
    assert loaded.status_code == 200
    assert loaded.json() == traced_map


@pytest.mark.asyncio
async def test_save_replaces_the_previous_map(
    async_client: AsyncClient, headers, strategy_scenario_id, traced_map
):
    await async_client.put(
        _path(strategy_scenario_id), json=traced_map, headers=headers
    )
    renamed = copy.deepcopy(traced_map)
    renamed["regions"][0]["name"] = "The Reach"

    await async_client.put(_path(strategy_scenario_id), json=renamed, headers=headers)
    loaded = await async_client.get(_path(strategy_scenario_id), headers=headers)

    assert loaded.json()["regions"][0]["name"] == "The Reach"


@pytest.mark.asyncio
async def test_get_before_first_save_is_404(
    async_client: AsyncClient, headers, strategy_scenario_id
):
    response = await async_client.get(_path(strategy_scenario_id), headers=headers)

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_save_accepts_a_picture_from_map_storage(
    async_client: AsyncClient, headers, strategy_scenario_id, traced_map
):
    traced_map["image_url"] = storage_client.public_url_for("scenario-maps/abc.png")

    response = await async_client.put(
        _path(strategy_scenario_id), json=traced_map, headers=headers
    )

    assert response.status_code == 200
    assert response.json()["image_url"] == traced_map["image_url"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "image_url",
    [
        "https://evil.example.com/map.png",
        storage_client.public_url_for("scenario-covers/abc.png"),
    ],
)
async def test_save_rejects_a_picture_not_from_map_storage(
    async_client: AsyncClient, headers, strategy_scenario_id, traced_map, image_url
):
    traced_map["image_url"] = image_url

    response = await async_client.put(
        _path(strategy_scenario_id), json=traced_map, headers=headers
    )

    assert response.status_code == 422
    assert "uploaded through" in response.json()["detail"]


def _with_duplicate_id(document: dict[str, object]) -> None:
    document["regions"][1]["id"] = document["regions"][0]["id"]


def _with_unknown_neighbor(document: dict[str, object]) -> None:
    document["regions"][0]["neighbor_ids"].append("region_99")


def _with_one_way_link(document: dict[str, object]) -> None:
    document["regions"][0]["neighbor_ids"].append("region_08")


def _with_unknown_road(document: dict[str, object]) -> None:
    document["roads"] = [{"region_a": "region_01", "region_b": "region_99"}]


def _with_island(document: dict[str, object]) -> None:
    for region in document["regions"]:
        region["neighbor_ids"] = []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("break_map", "expected_detail"),
    [
        (_with_duplicate_id, "used more than once"),
        (_with_unknown_neighbor, "unknown region 'region_99'"),
        (_with_unknown_road, "unknown region 'region_99'"),
        (_with_one_way_link, "but not the reverse"),
        (_with_island, "Map is not connected"),
    ],
)
async def test_save_rejects_a_structurally_broken_map(
    async_client: AsyncClient,
    headers,
    strategy_scenario_id,
    traced_map,
    break_map,
    expected_detail,
):
    break_map(traced_map)

    response = await async_client.put(
        _path(strategy_scenario_id), json=traced_map, headers=headers
    )

    assert response.status_code == 422
    assert expected_detail in response.json()["detail"]


@pytest.mark.asyncio
async def test_failed_save_keeps_the_previous_map(
    async_client: AsyncClient, headers, strategy_scenario_id, traced_map
):
    await async_client.put(
        _path(strategy_scenario_id), json=traced_map, headers=headers
    )
    broken = copy.deepcopy(traced_map)
    _with_island(broken)

    await async_client.put(_path(strategy_scenario_id), json=broken, headers=headers)
    loaded = await async_client.get(_path(strategy_scenario_id), headers=headers)

    assert loaded.json() == traced_map


@pytest.mark.asyncio
async def test_save_rejects_a_schema_violation(
    async_client: AsyncClient, headers, strategy_scenario_id, traced_map
):
    traced_map["regions"][0]["id"] = "Not A Valid Id"

    response = await async_client.put(
        _path(strategy_scenario_id), json=traced_map, headers=headers
    )

    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["newbie", "master"])
async def test_map_is_rejected_on_a_non_strategy_scenario(
    async_client: AsyncClient, headers, traced_map, mode
):
    scenario_id = await _create_scenario(async_client, headers, mode)

    saved = await async_client.put(_path(scenario_id), json=traced_map, headers=headers)
    loaded = await async_client.get(_path(scenario_id), headers=headers)

    assert saved.status_code == 422
    assert loaded.status_code == 422


@pytest.mark.asyncio
async def test_map_is_rejected_for_a_non_owner(
    async_client: AsyncClient, other_user, strategy_scenario_id, traced_map
):
    other_headers = {"x-dev-user-id": str(other_user.user_id)}

    saved = await async_client.put(
        _path(strategy_scenario_id), json=traced_map, headers=other_headers
    )
    loaded = await async_client.get(_path(strategy_scenario_id), headers=other_headers)

    assert saved.status_code == 403
    assert loaded.status_code == 403


@pytest.mark.asyncio
async def test_map_requires_authentication(
    async_client: AsyncClient, strategy_scenario_id, traced_map
):
    response = await async_client.put(_path(strategy_scenario_id), json=traced_map)

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_map_of_an_unknown_scenario_is_404(
    async_client: AsyncClient, headers, traced_map
):
    response = await async_client.put(
        _path(str(uuid.uuid4())), json=traced_map, headers=headers
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_save_is_rejected_while_publishing(
    async_client: AsyncClient,
    db_session: AsyncSession,
    headers,
    strategy_scenario_id,
    traced_map,
):
    from app.repositories.scenario_repo import ScenarioRepo

    scenario_repo = ScenarioRepo(db_session)
    scenario = await scenario_repo.get_by_id(uuid.UUID(strategy_scenario_id))
    scenario.status = "publishing"
    await scenario_repo.update(scenario)

    response = await async_client.put(
        _path(strategy_scenario_id), json=traced_map, headers=headers
    )

    assert response.status_code == 409

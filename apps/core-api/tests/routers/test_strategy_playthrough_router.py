"""Integration tests for starting a strategy playthrough (world initialization)."""

import uuid

import httpx
import pytest
import respx
from app.config import settings
from app.db.models.scenario import Scenario
from app.integrations import simulation_client
from app.repositories.playthrough_repo import PlaythroughRepo
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from strategy_contracts.examples import load_three_crowns

INITIALIZE_URL = f"{settings.simulation_url}{simulation_client.INITIALIZE_PATH}"
PLAYABLE_FACTION = "house_carrow"
NON_PLAYABLE_FACTION = "house_ashford"


@pytest.fixture(autouse=True)
def flush_instead_of_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    """The shared test session must roll back, so row-first commits only flush."""

    async def flush_only(self: PlaythroughRepo) -> None:
        await self.session.flush()

    monkeypatch.setattr(PlaythroughRepo, "commit", flush_only)


@pytest.fixture(autouse=True)
async def reset_simulation_client():
    await simulation_client.close_simulation_client()
    yield
    await simulation_client.close_simulation_client()


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    return await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )


@pytest.fixture
def headers(dev_user):
    return {"x-dev-user-id": str(dev_user.user_id)}


@pytest.fixture
async def strategy_scenario(db_session: AsyncSession, dev_user) -> Scenario:
    scenario = Scenario(
        creator_id=dev_user.user_id,
        title="Three Crowns",
        mode="strategy",
        complexity_tier="master",
        player_count_support="solo",
        status="published",
        strategy_document=load_three_crowns().model_dump(mode="json"),
    )
    db_session.add(scenario)
    await db_session.flush()
    return scenario


def _start(async_client: AsyncClient, headers, scenario: Scenario, faction: str | None):
    body: dict[str, object] = {"scenario_id": str(scenario.scenario_id)}
    if faction is not None:
        body["faction_id"] = faction
    return async_client.post("/v1/playthroughs", json=body, headers=headers)


@pytest.mark.asyncio
@respx.mock
async def test_start_creates_the_world_and_activates_the_playthrough(
    async_client: AsyncClient, headers, strategy_scenario
):
    route = respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(200, json={}))

    response = await _start(async_client, headers, strategy_scenario, PLAYABLE_FACTION)

    assert response.status_code == 201
    assert response.json()["status"] == "active"
    sent = route.calls.last.request
    payload = sent.read().decode()
    assert '"seed"' not in payload
    assert (
        f'"operation_id":"init:{response.json()["playthrough_id"]}"'
        in payload.replace(" ", "")
    )
    assert '"player_faction_id":"house_carrow"' in payload.replace(" ", "")


@pytest.mark.asyncio
@respx.mock
async def test_simulation_outage_leaves_the_playthrough_initializing_until_retry(
    async_client: AsyncClient, headers, strategy_scenario, db_session
):
    respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(503, json={}))

    failed = await _start(async_client, headers, strategy_scenario, PLAYABLE_FACTION)

    assert failed.status_code == 503
    row = (
        await PlaythroughRepo(db_session).list_by_scenario(
            strategy_scenario.scenario_id
        )
    )[0]
    assert row.status == "initializing"

    respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(200, json={}))
    retried = await async_client.post(
        f"/v1/playthroughs/{row.playthrough_id}/initialize", headers=headers
    )

    assert retried.status_code == 200
    assert retried.json()["status"] == "active"


@pytest.mark.asyncio
@respx.mock
async def test_simulation_rejection_surfaces_as_422(
    async_client: AsyncClient, headers, strategy_scenario
):
    respx.post(INITIALIZE_URL).mock(
        return_value=httpx.Response(422, json={"code": "invalid_scenario"})
    )

    response = await _start(async_client, headers, strategy_scenario, PLAYABLE_FACTION)

    assert response.status_code == 422
    assert response.json()["code"] == "simulation_rejected"


@pytest.mark.asyncio
@pytest.mark.parametrize("faction", [None, NON_PLAYABLE_FACTION, "nobody"])
async def test_start_requires_a_playable_faction(
    async_client: AsyncClient, headers, strategy_scenario, faction
):
    response = await _start(async_client, headers, strategy_scenario, faction)

    assert response.status_code == 422
    assert response.json()["code"] == "strategy_faction_invalid"


@pytest.mark.asyncio
async def test_start_rejects_a_leader_with_too_few_traits(
    async_client: AsyncClient, headers, strategy_scenario, db_session
):
    document = load_three_crowns().model_dump(mode="json")
    for leader in document["leaders"]:
        leader["trait_ids"] = leader["trait_ids"][:1]
    strategy_scenario.strategy_document = document
    await db_session.flush()

    response = await _start(async_client, headers, strategy_scenario, PLAYABLE_FACTION)

    assert response.status_code == 422
    assert response.json()["code"] == "strategy_ruler_invalid"


@pytest.mark.asyncio
@respx.mock
async def test_initializing_playthroughs_are_hidden_from_the_player_list(
    async_client: AsyncClient, headers, strategy_scenario, db_session
):
    respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(503, json={}))
    await _start(async_client, headers, strategy_scenario, PLAYABLE_FACTION)

    rows = await PlaythroughRepo(db_session).list_by_user_with_scenarios(
        strategy_scenario.creator_id
    )

    assert rows == []


@pytest.mark.asyncio
@respx.mock
async def test_create_strategy_playthrough_with_custom_ruler(
    async_client: AsyncClient,
    headers,
    strategy_scenario: Scenario,
    db_session: AsyncSession,
):
    document = load_three_crowns().model_dump(mode="json")
    for faction in document["factions"]:
        if faction["id"] == "house_ashford":
            faction["is_playable"] = True
    strategy_scenario.strategy_document = document
    await db_session.flush()

    route = respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(200, json={}))

    payload = {
        "scenario_id": str(strategy_scenario.scenario_id),
        "faction_id": "house_ashford",
        "player_ruler": {
            "name": "Queen Lysandra",
            "epithet": "The Shield of the Vale",
            "trait_ids": ["honorable", "cautious"],
            "ambition_ids": ["ambition_expand"],
            "backstory": "Crowned in spring.",
        },
    }
    response = await async_client.post(
        "/v1/playthroughs",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["playthrough_id"] is not None
    assert data["status"] == "active"

    sent = route.calls.last.request
    payload_sent = sent.read().decode()
    assert "Queen Lysandra" in payload_sent
    assert "The Shield of the Vale" in payload_sent
    assert "honorable" in payload_sent
    assert "cautious" in payload_sent
    assert "ambition_expand" in payload_sent
    assert "Crowned in spring." in payload_sent


@pytest.mark.asyncio
@respx.mock
async def test_retry_initialization_preserves_custom_ruler(
    async_client: AsyncClient,
    headers,
    strategy_scenario: Scenario,
    db_session: AsyncSession,
):
    document = load_three_crowns().model_dump(mode="json")
    for faction in document["factions"]:
        if faction["id"] == "house_ashford":
            faction["is_playable"] = True
    strategy_scenario.strategy_document = document
    await db_session.flush()

    respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(503, json={}))

    payload = {
        "scenario_id": str(strategy_scenario.scenario_id),
        "faction_id": "house_ashford",
        "player_ruler": {
            "name": "Queen Lysandra",
            "epithet": "The Shield of the Vale",
            "trait_ids": ["honorable", "cautious"],
            "ambition_ids": ["ambition_expand"],
            "backstory": "Crowned in spring.",
        },
    }
    failed = await async_client.post("/v1/playthroughs", json=payload, headers=headers)
    assert failed.status_code == 503

    row = (
        await PlaythroughRepo(db_session).list_by_scenario(
            strategy_scenario.scenario_id
        )
    )[0]
    assert row.status == "initializing"

    retry_route = respx.post(INITIALIZE_URL).mock(
        return_value=httpx.Response(200, json={})
    )
    retried = await async_client.post(
        f"/v1/playthroughs/{row.playthrough_id}/initialize", headers=headers
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "active"

    sent = retry_route.calls.last.request
    payload_sent = sent.read().decode()
    assert "Queen Lysandra" in payload_sent


@pytest.mark.asyncio
@respx.mock
async def test_creator_can_playtest_a_draft_strategy_scenario(
    async_client: AsyncClient, headers, strategy_scenario
):
    strategy_scenario.status = "draft"
    respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(200, json={}))

    response = await async_client.post(
        f"/v1/scenarios/{strategy_scenario.scenario_id}/playtest",
        json={"faction_id": PLAYABLE_FACTION},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["is_playtest"] is True
    assert body["status"] == "active"


@pytest.mark.asyncio
@respx.mock
async def test_strategy_playtest_requires_a_playable_faction(
    async_client: AsyncClient, headers, strategy_scenario
):
    route = respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(200, json={}))

    response = await async_client.post(
        f"/v1/scenarios/{strategy_scenario.scenario_id}/playtest",
        json={},
        headers=headers,
    )

    assert response.status_code == 422
    assert not route.called


@pytest.mark.asyncio
@respx.mock
async def test_starting_again_after_an_outage_resumes_the_stuck_playthrough(
    async_client: AsyncClient, headers, strategy_scenario, db_session
):
    respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(503, json={}))
    await _start(async_client, headers, strategy_scenario, PLAYABLE_FACTION)
    respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(200, json={}))

    second = await _start(async_client, headers, strategy_scenario, PLAYABLE_FACTION)

    assert second.status_code == 201
    assert second.json()["status"] == "active"
    rows = await PlaythroughRepo(db_session).list_by_scenario(
        strategy_scenario.scenario_id
    )
    assert len(rows) == 1
    assert str(rows[0].playthrough_id) == second.json()["playthrough_id"]


def _document_with_orders(orders_per_turn: int) -> dict[str, object]:
    document = load_three_crowns().model_dump(mode="json")
    document["tuning"]["orders_per_turn"] = orders_per_turn
    return document


@pytest.mark.asyncio
@respx.mock
async def test_a_real_run_plays_the_published_document_not_later_draft_edits(
    async_client: AsyncClient, headers, strategy_scenario
):
    strategy_scenario.published_strategy_document = _document_with_orders(3)
    strategy_scenario.strategy_document = _document_with_orders(9)
    route = respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(200, json={}))

    response = await _start(async_client, headers, strategy_scenario, PLAYABLE_FACTION)

    assert response.status_code == 201
    sent = route.calls.last.request.read().decode().replace(" ", "")
    assert '"orders_per_turn":3' in sent
    assert '"orders_per_turn":9' not in sent


@pytest.mark.asyncio
@respx.mock
async def test_a_playtest_plays_the_live_draft(
    async_client: AsyncClient, headers, strategy_scenario
):
    strategy_scenario.published_strategy_document = _document_with_orders(3)
    strategy_scenario.strategy_document = _document_with_orders(9)
    route = respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(200, json={}))

    response = await async_client.post(
        f"/v1/scenarios/{strategy_scenario.scenario_id}/playtest",
        json={"faction_id": PLAYABLE_FACTION},
        headers=headers,
    )

    assert response.status_code == 201
    sent = route.calls.last.request.read().decode().replace(" ", "")
    assert '"orders_per_turn":9' in sent


@pytest.mark.asyncio
@respx.mock
async def test_a_published_row_without_a_pinned_document_falls_back_to_the_live_one(
    async_client: AsyncClient, headers, strategy_scenario
):
    strategy_scenario.published_strategy_document = None
    strategy_scenario.strategy_document = _document_with_orders(9)
    route = respx.post(INITIALIZE_URL).mock(return_value=httpx.Response(200, json={}))

    response = await _start(async_client, headers, strategy_scenario, PLAYABLE_FACTION)

    assert response.status_code == 201
    assert '"orders_per_turn":9' in route.calls.last.request.read().decode().replace(
        " ", ""
    )

"""Integration and unit tests for strategy ruler backstory AI redraft endpoint."""

import uuid
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from app.config import settings
from app.exceptions.text_generation_exceptions import TextGenerationError
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from strategy_contracts.scenario import StrategyScenario


@pytest.fixture
async def dev_user(db_session: AsyncSession):
    user = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )
    token = jwt.encode(
        {
            "sub": str(user.user_id),
            "token_version": user.token_version,
            "type": "access",
        },
        settings.secret_key,
        algorithm=settings.jwt_algorithm,
    )
    user.token = token
    return user


@pytest.fixture
def auth_headers(dev_user):
    return {"Authorization": f"Bearer {dev_user.token}"}


@pytest.fixture
async def scenario_id(async_client: AsyncClient, auth_headers) -> str:
    response = await async_client.post(
        "/v1/scenarios",
        json={
            "title": "The Reach",
            "mode": "strategy",
            "strategy_document": StrategyScenario().model_dump(mode="json"),
        },
        headers=auth_headers,
    )
    assert response.status_code == 201
    return response.json()["scenario_id"]


@pytest.fixture
def sample_payload(scenario_id):
    return {
        "scenario_id": scenario_id,
        "faction_id": "valenreach",
        "ruler_name": "King Alden IV",
        "epithet": "Sovereign of the Marches",
        "trait_ids": ["honorable", "cautious"],
        "ambition_ids": ["ambition_peace"],
    }


@pytest.mark.asyncio
async def test_ruler_backstory_redraft_endpoint(
    async_client: AsyncClient, dev_user, auth_headers, sample_payload
):
    with patch(
        "app.routers.strategy_ruler.ruler_backstory_service.generate_ruler_backstory",
        new_callable=AsyncMock,
    ) as mock_gen:
        mock_gen.return_value = "Crowned amidst the autumn mists following the sudden passing of the Old King."
        response = await async_client.post(
            "/v1/strategy/ruler-backstory",
            json=sample_payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "autumn mists" in response.json()["backstory"]


@pytest.mark.asyncio
async def test_ruler_backstory_redraft_requires_authentication(
    async_client: AsyncClient, sample_payload
):
    response = await async_client.post(
        "/v1/strategy/ruler-backstory",
        json=sample_payload,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_ruler_backstory_redraft_maps_generation_failure_to_502(
    async_client: AsyncClient, dev_user, auth_headers, sample_payload
):
    with patch(
        "app.routers.strategy_ruler.ruler_backstory_service.generate_ruler_backstory",
        new_callable=AsyncMock,
    ) as mock_gen:
        mock_gen.side_effect = TextGenerationError()
        response = await async_client.post(
            "/v1/strategy/ruler-backstory",
            json=sample_payload,
            headers=auth_headers,
        )
        assert response.status_code == 502


@pytest.mark.asyncio
async def test_ruler_backstory_rejects_unknown_scenario(
    async_client: AsyncClient, dev_user, auth_headers, sample_payload
):
    with patch(
        "app.routers.strategy_ruler.ruler_backstory_service.generate_ruler_backstory",
        new_callable=AsyncMock,
    ) as mock_gen:
        response = await async_client.post(
            "/v1/strategy/ruler-backstory",
            json={**sample_payload, "scenario_id": str(uuid.uuid4())},
            headers=auth_headers,
        )
        assert response.status_code == 404
        mock_gen.assert_not_called()


@pytest.mark.asyncio
async def test_ruler_backstory_rejects_other_users_unpublished_scenario(
    async_client: AsyncClient, db_session, auth_headers, sample_payload
):
    stranger = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Stranger"
    )
    with patch(
        "app.routers.strategy_ruler.ruler_backstory_service.generate_ruler_backstory",
        new_callable=AsyncMock,
    ) as mock_gen:
        response = await async_client.post(
            "/v1/strategy/ruler-backstory",
            json=sample_payload,
            headers={"x-dev-user-id": str(stranger.user_id)},
        )
        assert response.status_code == 403
        mock_gen.assert_not_called()

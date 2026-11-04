"""Authored sub-resources are read-only while their scenario is publishing (ADR-14)."""

import uuid

import pytest
from app.repositories.scenario_repo import ScenarioRepo
from app.repositories.user_repo import UserRepo
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

ANY_ID = str(uuid.uuid4())
OTHER_ID = str(uuid.uuid4())

MINIGAME_BODY = {
    "label": "Dodge the boulder",
    "minigame_type": "dodge",
    "outcome_mode": "binary",
    "win_mutation": {"path": "player.health", "op": "set", "value": 100},
    "lose_mutation": {"path": "player.health", "op": "decrement", "value": 15},
    "dodge_config": {"difficulty": 3},
}

WRITE_ROUTES: list[tuple[str, str, dict[str, object] | None]] = [
    ("POST", "entities", {"entity_type": "character", "canonical_name": "Warden"}),
    ("PATCH", f"entities/{ANY_ID}", {"canonical_name": "Warden"}),
    ("DELETE", f"entities/{ANY_ID}", None),
    ("POST", "entity-types", {"type_key": "relic", "display_label": "Relic"}),
    ("PATCH", f"entity-types/{ANY_ID}", {"display_label": "Relic"}),
    ("DELETE", f"entity-types/{ANY_ID}", None),
    (
        "POST",
        "facts",
        {"subject_entity_id": ANY_ID, "predicate": "guards", "object_literal": "x"},
    ),
    ("PATCH", f"facts/{ANY_ID}", {"predicate": "guards"}),
    ("DELETE", f"facts/{ANY_ID}", None),
    ("POST", "conditions", {"label": "Storm", "narrator_instruction": "Rain."}),
    ("PATCH", f"conditions/{ANY_ID}", {"label": "Storm"}),
    ("DELETE", f"conditions/{ANY_ID}", None),
    (
        "POST",
        "end_conditions",
        {"outcome_tag": "win", "outcome_title": "Won", "outcome_text": "Yay"},
    ),
    ("POST", "end_conditions/reorder", {"ordered_end_condition_ids": [ANY_ID]}),
    ("PATCH", f"end_conditions/{ANY_ID}", {"outcome_title": "Won"}),
    ("DELETE", f"end_conditions/{ANY_ID}", None),
    (
        "POST",
        "invariants",
        {
            "label": "Cap",
            "invariant_expression": {},
            "applies_to": "global",
            "narrator_text": "No.",
        },
    ),
    ("PATCH", f"invariants/{ANY_ID}", {"label": "Cap"}),
    ("DELETE", f"invariants/{ANY_ID}", None),
    ("POST", "minigames", MINIGAME_BODY),
    ("POST", "minigames/reorder", {"ordered_minigame_ids": [ANY_ID]}),
    ("PATCH", f"minigames/{ANY_ID}", {"label": "Dodge"}),
    ("DELETE", f"minigames/{ANY_ID}", None),
    ("POST", "maps", {"name": "Overworld"}),
    ("PATCH", f"maps/{ANY_ID}", {"name": "Overworld"}),
    ("DELETE", f"maps/{ANY_ID}", None),
    ("POST", f"maps/{ANY_ID}/pins", {"entity_id": ANY_ID, "x": 0.5, "y": 0.5}),
    ("PATCH", f"maps/{ANY_ID}/pins/{OTHER_ID}", {"x": 0.5}),
    ("DELETE", f"maps/{ANY_ID}/pins/{OTHER_ID}", None),
    ("POST", "map-connections", {"entity_id_a": ANY_ID, "entity_id_b": OTHER_ID}),
    ("DELETE", f"map-connections/{ANY_ID}", None),
]

READ_ROUTES = [
    "entities",
    "entity-types",
    "facts",
    "conditions",
    "end_conditions",
    "invariants",
    "minigames",
    "maps",
    "map-connections",
]


@pytest.fixture
async def creator_headers(db_session: AsyncSession) -> dict[str, str]:
    creator = await UserRepo(db_session).create(
        auth_provider_id=f"dev-auth-{uuid.uuid4()}", display_name="Dev Creator"
    )
    return {"x-dev-user-id": str(creator.user_id)}


@pytest.fixture
async def publishing_scenario_id(
    async_client: AsyncClient, db_session: AsyncSession, creator_headers
) -> str:
    response = await async_client.post(
        "/v1/scenarios",
        json={"title": "Mid-Publish", "mode": "master", "complexity_tier": "master"},
        headers=creator_headers,
    )
    assert response.status_code == 201
    scenario_id = response.json()["scenario_id"]
    scenario_repo = ScenarioRepo(db_session)
    scenario = await scenario_repo.get_by_id(uuid.UUID(scenario_id))
    scenario.status = "publishing"
    await scenario_repo.update(scenario)
    return scenario_id


@pytest.mark.asyncio
@pytest.mark.parametrize(("method", "path", "body"), WRITE_ROUTES)
async def test_write_rejected_while_publishing(
    async_client: AsyncClient,
    creator_headers,
    publishing_scenario_id: str,
    method: str,
    path: str,
    body: dict[str, object] | None,
):
    response = await async_client.request(
        method,
        f"/v1/scenarios/{publishing_scenario_id}/{path}",
        json=body,
        headers=creator_headers,
    )
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
@pytest.mark.parametrize("path", READ_ROUTES)
async def test_read_allowed_while_publishing(
    async_client: AsyncClient, creator_headers, publishing_scenario_id: str, path: str
):
    response = await async_client.get(
        f"/v1/scenarios/{publishing_scenario_id}/{path}", headers=creator_headers
    )
    assert response.status_code == 200, response.text

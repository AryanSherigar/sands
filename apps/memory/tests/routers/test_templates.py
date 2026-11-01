"""POST /v1/templates over ASGI with the real service on the test database."""

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
from app.main import create_app
from app.services.template_service import TemplateService, get_template_service
from httpx import ASGITransport, AsyncClient, Response
from psycopg import AsyncConnection
from tests.services.template_helpers import build_hollow_cairn

TEMPLATES_URL = "/v1/templates"
STATUS_CREATED = 201
STATUS_OK = 200
STATUS_CONFLICT = 409
STATUS_UNPROCESSABLE = 422


@pytest.fixture
async def client(db_connection: AsyncConnection) -> AsyncIterator[AsyncClient]:
    app = create_app()
    app.dependency_overrides[get_template_service] = lambda: TemplateService(
        db_connection
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http
    app.dependency_overrides.clear()


async def _post(client: AsyncClient, body: str) -> Response:
    return await client.post(
        TEMPLATES_URL, content=body, headers={"content-type": "application/json"}
    )


async def test_first_post_creates_and_identical_replay_returns_200(
    client: AsyncClient,
) -> None:
    body = build_hollow_cairn().request.model_dump_json()

    created = await _post(client, body)
    replayed = await _post(client, body)

    assert created.status_code == STATUS_CREATED
    assert created.json()["direct_status"] == "ready"
    assert created.json()["enrichment_status"] == "not_needed"
    assert replayed.status_code == STATUS_OK
    assert replayed.json() == created.json()


async def test_same_revision_with_different_hash_returns_409(
    client: AsyncClient,
) -> None:
    request = build_hollow_cairn().request
    await _post(client, request.model_dump_json())
    changed = request.model_copy(update={"content_hash": "different"})

    result = await _post(client, changed.model_dump_json())

    assert result.status_code == STATUS_CONFLICT
    assert result.json()["code"] == "template_content_conflict"


async def test_invalid_content_returns_422_invalid_template(
    client: AsyncClient,
) -> None:
    request = build_hollow_cairn().request
    request.master.facts[0].subject_entity_id = uuid4()

    result = await _post(client, request.model_dump_json())

    assert result.status_code == STATUS_UNPROCESSABLE
    assert result.json()["code"] == "invalid_template"


async def test_malformed_body_returns_422(client: AsyncClient) -> None:
    result = await _post(client, '{"scenario_id": "not-a-uuid"}')

    assert result.status_code == STATUS_UNPROCESSABLE

from collections.abc import AsyncIterator

import pytest
from app.db.pool import get_connection
from app.main import create_app
from httpx import ASGITransport, AsyncClient
from psycopg import AsyncConnection
from tests.middleware.helpers import TEST_SECRET, make_token, set_settings
from tests.repositories.helpers import OWNER_USER_ID


@pytest.fixture
async def api(
    db_connection: AsyncConnection, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    set_settings(monkeypatch, secret_key=TEST_SECRET, internal_service_token="internal")
    await db_connection.set_autocommit(True)
    application = create_app()

    async def connection() -> AsyncIterator[AsyncConnection]:
        yield db_connection

    application.dependency_overrides[get_connection] = connection
    headers = {"Authorization": f"Bearer {make_token(sub=str(OWNER_USER_ID))}"}
    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
        headers=headers,
    ) as client:
        yield client

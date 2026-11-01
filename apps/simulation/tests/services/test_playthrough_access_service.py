from uuid import UUID, uuid4

import pytest
from app.db.pool import get_connection
from app.exceptions.access_exceptions import PlaythroughNotFoundError
from app.middleware.error_handler import setup_error_handlers
from app.models.persistence import PlaythroughRow
from app.services.playthrough_access_service import (
    PlaythroughAccessService,
    get_owned_playthrough,
)
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import OWNER_USER_ID, seed_playthrough

OTHER_USER_ID = UUID("99999999-9999-9999-9999-999999999999")


async def test_owner_gets_the_playthrough(db_connection) -> None:
    await seed_playthrough(db_connection)
    service = PlaythroughAccessService(db_connection)
    row = await service.require_owned_playthrough(PLAYTHROUGH_ID, OWNER_USER_ID)
    assert row.playthrough_id == PLAYTHROUGH_ID


async def test_another_user_is_refused(db_connection) -> None:
    await seed_playthrough(db_connection)
    service = PlaythroughAccessService(db_connection)
    with pytest.raises(PlaythroughNotFoundError):
        await service.require_owned_playthrough(PLAYTHROUGH_ID, OTHER_USER_ID)


async def test_unknown_playthrough_is_refused(db_connection) -> None:
    service = PlaythroughAccessService(db_connection)
    with pytest.raises(PlaythroughNotFoundError):
        await service.require_owned_playthrough(uuid4(), OWNER_USER_ID)


def _client(db_connection) -> TestClient:
    app = FastAPI()
    setup_error_handlers(app)

    @app.get("/v1/playthroughs/{playthrough_id}/whoami")
    async def whoami(
        playthrough: PlaythroughRow = Depends(get_owned_playthrough),
    ) -> dict[str, str]:
        return {"playthrough_id": str(playthrough.playthrough_id)}

    async def shared_connection():
        yield db_connection

    app.dependency_overrides[get_connection] = shared_connection
    return TestClient(app)


async def test_unknown_and_foreign_playthroughs_look_identical(db_connection) -> None:
    await seed_playthrough(db_connection)
    client = _client(db_connection)
    foreign = client.get(
        f"/v1/playthroughs/{PLAYTHROUGH_ID}/whoami",
        headers={"x-dev-user-id": str(OTHER_USER_ID)},
    )
    unknown = client.get(
        f"/v1/playthroughs/{uuid4()}/whoami",
        headers={"x-dev-user-id": str(OTHER_USER_ID)},
    )
    assert (foreign.status_code, foreign.content) == (
        unknown.status_code,
        unknown.content,
    )
    assert foreign.status_code == 404


async def test_owner_reaches_the_route(db_connection) -> None:
    await seed_playthrough(db_connection)
    response = _client(db_connection).get(
        f"/v1/playthroughs/{PLAYTHROUGH_ID}/whoami",
        headers={"x-dev-user-id": str(OWNER_USER_ID)},
    )
    assert response.status_code == 200
    assert response.json() == {"playthrough_id": str(PLAYTHROUGH_ID)}

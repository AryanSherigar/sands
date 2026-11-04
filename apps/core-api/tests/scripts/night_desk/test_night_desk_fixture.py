"""The checked-in engine fixture must equal what the generator pins today.

The Turn Resolution Service's Night Desk tests replay this file (a real pinned
snapshot plus the initial state) so they never import the Core API generator.
Regenerate with:
    REGENERATE_NIGHT_DESK_FIXTURE=1 .venv/bin/python -m pytest \
        tests/scripts/night_desk/test_night_desk_fixture.py -q
"""

import json
import os
import uuid
from pathlib import Path

import pytest
from app.db.models.playthrough import Playthrough
from app.db.models.user import User
from app.models.playthrough import PlaythroughCreate
from app.repositories.user_repo import UserRepo
from scripts.night_desk.builder import build
from scripts.night_desk.ids import SCENARIO_ID
from scripts.night_desk.persist import persist
from scripts.night_desk.playtest import create_playtest
from sqlalchemy.ext.asyncio import AsyncSession

REGENERATE_VARIABLE = "REGENERATE_NIGHT_DESK_FIXTURE"
FIXTURE_PATH = (
    Path(__file__).resolve().parents[5]
    / "apps/turn-resolution-service/tests/turn/fixtures/night_desk_export.json"
)
PLAYER_NAME = "Alex"
SEED_PLACEHOLDER = "r6"


@pytest.fixture
async def creator(db_session: AsyncSession) -> User:
    return await UserRepo(db_session).create(
        auth_provider_id=f"test-auth-{uuid.uuid4()}", display_name="Creator"
    )


async def _render_fixture(db_session: AsyncSession, creator: User) -> str:
    await persist(db_session, build(), creator.user_id)
    data = PlaythroughCreate(
        scenario_id=SCENARIO_ID, setup_values={"character_name": PLAYER_NAME}
    )
    response = await create_playtest(db_session, creator.user_id, data)
    row = await db_session.get(Playthrough, response.playthrough_id)
    initial_state = {**row.state, "seed": {"false_rule": SEED_PLACEHOLDER}}
    payload = {"snapshot": row.scenario_snapshot, "initial_state": initial_state}
    return json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n"


@pytest.mark.asyncio
async def test_the_engine_fixture_is_current(db_session: AsyncSession, creator: User):
    rendered = await _render_fixture(db_session, creator)
    if os.environ.get(REGENERATE_VARIABLE):
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_PATH.write_text(rendered, encoding="utf-8")
    assert FIXTURE_PATH.read_text(encoding="utf-8") == rendered, (
        f"night_desk_export.json is stale; regenerate with {REGENERATE_VARIABLE}=1"
    )

import json
import uuid

import pytest
from app.repositories.endings_repo import EndingsRepo
from app.services.endings_service import EndingsService
from sqlalchemy.ext.asyncio import AsyncSession
from tests.stats_factories import add_playthrough, make_scenario, make_user


def snapshot(*entries):
    return {
        "end_conditions": [
            {
                "outcome_title": title,
                "outcome_tag": "win",
                "is_secret": is_secret,
                "priority": index,
                "end_condition_id": str(condition_id),
            }
            for index, (title, is_secret, condition_id) in enumerate(entries)
        ]
    }


@pytest.mark.asyncio
async def test_zero_history_and_newbie_only_users_get_no_scenarios(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    newbie = await make_scenario(db_session, user, mode="newbie")
    await add_playthrough(db_session, newbie, user, turn_count=4)
    result = await EndingsService(EndingsRepo(db_session)).get_endings(user.user_id)
    assert result.scenarios == []


@pytest.mark.asyncio
async def test_endings_combine_snapshot_and_finished_runs(
    db_session: AsyncSession,
) -> None:
    user = await make_user(db_session)
    scenario = await make_scenario(db_session, user, mode="master")
    ashen, vigil, consumed = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    snap = snapshot(
        ("Ashen", False, ashen),
        ("The Vigil", True, vigil),
        ("Consumed", False, consumed),
    )
    await add_playthrough(
        db_session,
        scenario,
        user,
        turn_count=6,
        status="completed",
        outcome_tag="win",
        outcome_title="Ashen",
        outcome_id=ashen,
        snapshot=snap,
    )
    await add_playthrough(db_session, scenario, user, turn_count=2, snapshot=snap)

    result = await EndingsService(EndingsRepo(db_session)).get_endings(user.user_id)

    (story,) = result.scenarios
    assert (story.found_count, story.total_count) == (1, 2)  # Vigil stays hidden
    raw = json.dumps(result.model_dump(mode="json"))
    assert "Vigil" not in raw
    assert "Consumed" not in raw

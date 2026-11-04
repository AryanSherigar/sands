import uuid

from app.db.models.scenario import Scenario
from app.db.models.user import User
from app.services.welcome_tape_service import enable_welcome_tape
from sqlalchemy.ext.asyncio import AsyncSession


async def test_enable_tape_preserves_existing_scenario(
    db_session: AsyncSession,
) -> None:
    owner = User(auth_provider_id=str(uuid.uuid4()), display_name="Owner")
    db_session.add(owner)
    await db_session.flush()
    scenario = Scenario(
        creator_id=owner.user_id,
        title="Night Desk",
        mode="master",
        complexity_tier="master",
        player_count_support="solo",
        world_data={"openingPrompt": "Unchanged", "presentation": {"other": "kept"}},
        setup_schema=[{"key": "character_name"}],
    )
    db_session.add(scenario)
    await db_session.flush()
    await enable_welcome_tape(db_session, scenario.scenario_id)
    await enable_welcome_tape(db_session, scenario.scenario_id)
    assert scenario.title == "Night Desk"
    assert scenario.setup_schema == [{"key": "character_name"}]
    assert scenario.world_data == {
        "openingPrompt": "Unchanged",
        "presentation": {"other": "kept", "welcome_tape_id": "tallis-v1"},
    }

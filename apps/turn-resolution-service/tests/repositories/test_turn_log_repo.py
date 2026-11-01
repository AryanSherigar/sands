"""Integration tests for TurnLogRepo against a real test Postgres instance."""

import uuid

import pytest
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from app.repositories.turn_log_repo import TurnLogRepo
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _seed_playthrough(session: AsyncSession) -> Playthrough:
    # IDs generated explicitly: the ORM column's default=uuid.uuid4 only fires
    # at flush/INSERT time, not at object construction.
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    user = User(
        user_id=user_id, display_name="Tester", auth_provider_id=str(uuid.uuid4())
    )
    scenario = Scenario(
        scenario_id=scenario_id,
        creator_id=user_id,
        title="Test Scenario",
        mode="newbie",
        complexity_tier="newbie",
        player_count_support="solo",
    )
    session.add(user)
    await session.flush()
    session.add(scenario)
    await session.flush()

    playthrough = Playthrough(
        scenario_id=scenario_id, created_by=user_id, scenario_version=1
    )
    session.add(playthrough)
    await session.flush()
    return playthrough


async def test_create_persists_turn_log_row(db_session: AsyncSession) -> None:
    playthrough = await _seed_playthrough(db_session)
    repo = TurnLogRepo(db_session)

    created = await repo.create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=1,
        participant_id=None,
        action_text="I look around.",
        narration_text="You see a torchlit corridor.",
    )

    stmt = select(TurnLog).where(TurnLog.turn_id == created.turn_id)
    result = await db_session.execute(stmt)
    fetched = result.scalars().first()

    assert fetched is not None
    assert fetched.playthrough_id == playthrough.playthrough_id
    assert fetched.turn_number == 1
    assert fetched.action_text == "I look around."
    assert fetched.action_mode == "do"
    assert fetched.narration_text == "You see a torchlit corridor."
    assert fetched.tool_calls == []


async def test_create_persists_the_given_action_mode(
    db_session: AsyncSession,
) -> None:
    playthrough = await _seed_playthrough(db_session)
    repo = TurnLogRepo(db_session)

    created = await repo.create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=1,
        participant_id=None,
        action_text="I whisper to the Warden.",
        narration_text="The Warden stirs.",
        action_mode="say",
    )

    assert created.action_mode == "say"


async def test_create_duplicate_turn_number_raises_integrity_error(
    db_session: AsyncSession,
) -> None:
    playthrough = await _seed_playthrough(db_session)
    repo = TurnLogRepo(db_session)

    await repo.create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=1,
        participant_id=None,
        action_text="Turn 1 action.",
        narration_text="Turn 1 narration.",
    )

    with pytest.raises(IntegrityError):
        await repo.create(
            playthrough_id=playthrough.playthrough_id,
            turn_number=1,
            participant_id=None,
            action_text="Duplicate turn 1 action.",
            narration_text="Duplicate turn 1 narration.",
        )


async def test_find_latest_by_location_returns_most_recent_matching_row(
    db_session: AsyncSession,
) -> None:
    playthrough = await _seed_playthrough(db_session)
    repo = TurnLogRepo(db_session)

    await repo.create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=1,
        participant_id=None,
        action_text="I look around.",
        narration_text="A dim hall.",
        image_url="https://example.com/first.png",
        location_id="loc-1",
        scene_image_prompt="first prompt",
    )
    await repo.create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=2,
        participant_id=None,
        action_text="I look again.",
        narration_text="Still the dim hall.",
        image_url="https://example.com/second.png",
        location_id="loc-1",
        scene_image_prompt="second prompt",
    )

    found = await repo.find_latest_by_location(playthrough.playthrough_id, "loc-1")

    assert found is not None
    assert found.scene_image_prompt == "second prompt"


async def test_find_latest_by_location_ignores_other_locations(
    db_session: AsyncSession,
) -> None:
    playthrough = await _seed_playthrough(db_session)
    repo = TurnLogRepo(db_session)

    await repo.create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=1,
        participant_id=None,
        action_text="I look around.",
        narration_text="A dim hall.",
        image_url="https://example.com/first.png",
        location_id="loc-1",
        scene_image_prompt="first prompt",
    )

    found = await repo.find_latest_by_location(playthrough.playthrough_id, "loc-2")

    assert found is None


async def test_create_persists_client_action_id_and_finds_it_by_playthrough(
    db_session: AsyncSession,
) -> None:
    playthrough = await _seed_playthrough(db_session)
    other_playthrough = await _seed_playthrough(db_session)
    repo = TurnLogRepo(db_session)
    client_action_id = uuid.uuid4()
    created = await repo.create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=1,
        participant_id=None,
        action_text="I look around.",
        narration_text="A corridor.",
        client_action_id=client_action_id,
    )

    found = await repo.get_by_client_action_id(
        playthrough.playthrough_id, client_action_id
    )
    in_other_playthrough = await repo.get_by_client_action_id(
        other_playthrough.playthrough_id, client_action_id
    )
    unknown = await repo.get_by_client_action_id(
        playthrough.playthrough_id, uuid.uuid4()
    )

    assert found is not None and found.turn_id == created.turn_id
    assert in_other_playthrough is None
    assert unknown is None


async def test_duplicate_client_action_id_in_one_playthrough_is_rejected(
    db_session: AsyncSession,
) -> None:
    playthrough = await _seed_playthrough(db_session)
    repo = TurnLogRepo(db_session)
    client_action_id = uuid.uuid4()
    await repo.create(
        playthrough_id=playthrough.playthrough_id,
        turn_number=1,
        participant_id=None,
        action_text="First.",
        narration_text="One.",
        client_action_id=client_action_id,
    )

    with pytest.raises(IntegrityError):
        await repo.create(
            playthrough_id=playthrough.playthrough_id,
            turn_number=2,
            participant_id=None,
            action_text="Second.",
            narration_text="Two.",
            client_action_id=client_action_id,
        )


async def test_list_recent_returns_newest_rows_oldest_first(
    db_session: AsyncSession,
) -> None:
    playthrough = await _seed_playthrough(db_session)
    other_playthrough = await _seed_playthrough(db_session)
    repo = TurnLogRepo(db_session)
    for turn_number in range(1, 9):
        await repo.create(
            playthrough_id=playthrough.playthrough_id,
            turn_number=turn_number,
            participant_id=None,
            action_text=f"action {turn_number}",
            narration_text=f"narration {turn_number}",
        )
    await repo.create(
        playthrough_id=other_playthrough.playthrough_id,
        turn_number=1,
        participant_id=None,
        action_text="other playthrough",
        narration_text="other",
    )

    recent = await repo.list_recent(playthrough.playthrough_id, 6)

    assert [row.turn_number for row in recent] == [3, 4, 5, 6, 7, 8]


async def test_list_recent_with_fewer_rows_than_limit_returns_all(
    db_session: AsyncSession,
) -> None:
    playthrough = await _seed_playthrough(db_session)
    repo = TurnLogRepo(db_session)
    for turn_number in (1, 2):
        await repo.create(
            playthrough_id=playthrough.playthrough_id,
            turn_number=turn_number,
            participant_id=None,
            action_text="a",
            narration_text="n",
        )

    recent = await repo.list_recent(playthrough.playthrough_id, 6)

    assert [row.turn_number for row in recent] == [1, 2]
    assert await repo.list_recent(uuid.uuid4(), 6) == []

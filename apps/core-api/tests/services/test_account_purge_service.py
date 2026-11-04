from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from app.config import settings
from app.db.models.memory_outbox import MemoryOutbox
from app.db.models.memory_relay_claim import MemoryRelayClaim
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.turn_log import TurnLog
from app.db.models.user import User
from app.exceptions.memory_exceptions import MemoryPurgeError
from app.models.memory_purge import MemoryPurgeResult
from app.repositories.account_purge_repo import AccountPurgeRepo
from app.repositories.memory_outbox_repo import MemoryOutboxRepo
from app.repositories.user_repo import UserRepo
from app.services.account_purge_service import AccountPurgeService
from sqlalchemy import select, update
from tests.stats_factories import (
    add_playthrough,
    add_turn_log,
    make_scenario,
    make_user,
)

EXPIRED = datetime.now(UTC) - timedelta(days=settings.account_deletion_grace_days + 1)
RECENT_REQUEST = datetime.now(UTC) - timedelta(days=1)


def _build_service(session) -> AccountPurgeService:
    return AccountPurgeService(session, AccountPurgeRepo(session), UserRepo(session))


async def _exists(session, model, **filters) -> bool:
    stmt = select(model)
    for column, value in filters.items():
        stmt = stmt.where(getattr(model, column) == value)
    return (await session.execute(stmt)).scalars().first() is not None


@pytest.fixture(autouse=True)
def stub_external_systems():
    with (
        patch(
            "app.services.account_purge_service.identity_client.delete_identity",
            new_callable=AsyncMock,
        ) as delete_identity,
        patch(
            "app.services.account_purge_service.storage_client.delete_object",
            new_callable=AsyncMock,
        ) as delete_object,
    ):
        yield delete_identity, delete_object


@pytest.fixture(autouse=True)
def memory_purge():
    with patch(
        "app.services.account_purge_service.memory_client.purge",
        new_callable=AsyncMock,
        return_value=MemoryPurgeResult(),
    ) as purge:
        yield purge


@pytest_asyncio.fixture(autouse=True)
async def forgive_users_left_due(db_session):
    """Skipped users stay due and are committed with the session; clear them so
    later tests only see their own users."""
    yield
    await db_session.rollback()
    await db_session.execute(update(User).values(deletion_requested_at=None))
    await db_session.commit()


@pytest.mark.asyncio
async def test_purge_skips_accounts_inside_grace_period(db_session) -> None:
    user = await make_user(db_session)
    user.deletion_requested_at = RECENT_REQUEST
    await db_session.flush()

    result = await _build_service(db_session).purge_expired_accounts()

    assert result.purged == 0
    assert await _exists(db_session, User, user_id=user.user_id)


@pytest.mark.asyncio
async def test_purge_ignores_accounts_never_flagged(db_session) -> None:
    user = await make_user(db_session)

    await _build_service(db_session).purge_expired_accounts()

    assert await _exists(db_session, User, user_id=user.user_id)


@pytest.mark.asyncio
async def test_purge_deletes_personal_data_and_the_user(
    db_session, stub_external_systems
) -> None:
    delete_identity, _ = stub_external_systems
    user = await make_user(db_session)
    other = await make_user(db_session)
    scenario = await make_scenario(db_session, other)
    playthrough = await add_playthrough(db_session, scenario, user)
    await add_turn_log(db_session, playthrough, 1, datetime.now(UTC))
    user.deletion_requested_at = EXPIRED
    await db_session.flush()

    result = await _build_service(db_session).purge_expired_accounts()

    assert result.purged == 1
    assert not await _exists(db_session, User, user_id=user.user_id)
    assert not await _exists(
        db_session, Playthrough, playthrough_id=playthrough.playthrough_id
    )
    assert not await _exists(
        db_session, TurnLog, playthrough_id=playthrough.playthrough_id
    )
    assert await _exists(db_session, Scenario, scenario_id=scenario.scenario_id)
    delete_identity.assert_awaited_once_with(user.auth_provider_id)


@pytest.mark.asyncio
async def test_purge_deletes_outbox_rows_of_purged_playthroughs_only(
    db_session,
) -> None:
    user = await make_user(db_session)
    other = await make_user(db_session)
    scenario = await make_scenario(db_session, other)
    purged = await add_playthrough(db_session, scenario, user)
    kept = await add_playthrough(db_session, scenario, other)
    outbox = MemoryOutboxRepo(db_session)
    await outbox.add_register_row(purged.playthrough_id, {})
    await outbox.add_register_row(kept.playthrough_id, {})
    for playthrough in (purged, kept):
        db_session.add(
            MemoryRelayClaim(
                playthrough_id=playthrough.playthrough_id,
                delivery_id=uuid4(),
                ownership_token=uuid4(),
                lease_expires_at=datetime.now(UTC),
                outbox_ids=[],
                payload={"private": "player narration"},
            )
        )
    user.deletion_requested_at = EXPIRED
    await db_session.flush()

    await _build_service(db_session).purge_expired_accounts()

    assert not await _exists(
        db_session, MemoryOutbox, playthrough_id=purged.playthrough_id
    )
    assert await _exists(db_session, MemoryOutbox, playthrough_id=kept.playthrough_id)

    assert not await _exists(
        db_session, MemoryRelayClaim, playthrough_id=purged.playthrough_id
    )
    assert await _exists(
        db_session, MemoryRelayClaim, playthrough_id=kept.playthrough_id
    )


@pytest.mark.asyncio
async def test_purge_anonymises_published_and_deletes_draft_scenarios(
    db_session,
) -> None:
    user = await make_user(db_session)
    published = await make_scenario(db_session, user, status="published")
    draft = await make_scenario(db_session, user, status="draft")
    user.deletion_requested_at = EXPIRED
    await db_session.flush()

    await _build_service(db_session).purge_expired_accounts()
    await db_session.refresh(published)

    assert published.creator_id == settings.deleted_user_id
    assert not await _exists(db_session, Scenario, scenario_id=draft.scenario_id)
    placeholder = await db_session.get(User, settings.deleted_user_id)
    assert placeholder is not None
    assert placeholder.display_name == "Deleted user"


@pytest.mark.asyncio
async def test_purge_keeps_unpublished_scenario_others_still_play(
    db_session,
) -> None:
    user = await make_user(db_session)
    player = await make_user(db_session)
    archived = await make_scenario(db_session, user, status="archived")
    await add_playthrough(db_session, archived, player)
    user.deletion_requested_at = EXPIRED
    await db_session.flush()

    await _build_service(db_session).purge_expired_accounts()
    await db_session.refresh(archived)

    assert archived.creator_id == settings.deleted_user_id


@pytest.mark.asyncio
async def test_purge_deletes_owned_media_and_is_rerunnable(
    db_session, stub_external_systems
) -> None:
    _, delete_object = stub_external_systems
    user = await make_user(db_session)
    user.avatar_url = "http://localhost:8000/uploads/avatars/a.png"
    user.deletion_requested_at = EXPIRED
    await db_session.flush()
    service = _build_service(db_session)

    first = await service.purge_expired_accounts()
    second = await service.purge_expired_accounts()

    assert (first.purged, second.purged) == (1, 0)
    delete_object.assert_awaited_once_with(user.avatar_url)


@pytest.mark.asyncio
async def test_purge_survives_media_delete_failure(
    db_session, stub_external_systems
) -> None:
    _, delete_object = stub_external_systems
    delete_object.side_effect = RuntimeError("storage down")
    user = await make_user(db_session)
    user.banner_url = "http://localhost:8000/uploads/banners/b.png"
    user.deletion_requested_at = EXPIRED
    await db_session.flush()

    await _build_service(db_session).purge_expired_accounts()

    assert not await _exists(db_session, User, user_id=user.user_id)


async def _due_user_with_playthrough(db_session, scenario, minutes: int = 0):
    user = await make_user(db_session)
    playthrough = await add_playthrough(db_session, scenario, user)
    await MemoryOutboxRepo(db_session).add_register_row(playthrough.playthrough_id, {})
    user.deletion_requested_at = EXPIRED + timedelta(minutes=minutes)
    await db_session.flush()
    return user, playthrough


@pytest.mark.asyncio
async def test_memory_is_purged_after_outbox_rows_and_before_product_rows(
    db_session, memory_purge
) -> None:
    owner = await make_user(db_session)
    scenario = await make_scenario(db_session, owner)
    user, playthrough = await _due_user_with_playthrough(db_session, scenario)
    seen: dict[str, bool] = {}

    async def record_state(playthrough_ids=None, scenario_ids=None):
        seen["has_outbox_rows"] = await _exists(
            db_session, MemoryOutbox, playthrough_id=playthrough.playthrough_id
        )
        seen["has_playthrough"] = await _exists(
            db_session, Playthrough, playthrough_id=playthrough.playthrough_id
        )
        return MemoryPurgeResult()

    memory_purge.side_effect = record_state

    await _build_service(db_session).purge_expired_accounts()

    assert seen == {"has_outbox_rows": False, "has_playthrough": True}
    memory_purge.assert_any_await(playthrough_ids=[playthrough.playthrough_id])
    assert not await _exists(db_session, User, user_id=user.user_id)


@pytest.mark.asyncio
async def test_a_memory_failure_skips_the_user_and_keeps_their_rows(
    db_session, memory_purge, stub_external_systems
) -> None:
    delete_identity, _ = stub_external_systems
    owner = await make_user(db_session)
    scenario = await make_scenario(db_session, owner)
    user, playthrough = await _due_user_with_playthrough(db_session, scenario)
    memory_purge.side_effect = MemoryPurgeError("unavailable")
    service = _build_service(db_session)

    result = await service.purge_expired_accounts()

    assert (result.purged, result.skipped, result.is_aborted) == (0, 1, False)
    assert await _exists(db_session, User, user_id=user.user_id)
    assert await _exists(
        db_session, Playthrough, playthrough_id=playthrough.playthrough_id
    )
    delete_identity.assert_not_awaited()

    memory_purge.side_effect = None
    memory_purge.return_value = MemoryPurgeResult(playthroughs_purged=1)
    retry = await service.purge_expired_accounts()

    assert retry.purged == 1
    assert not await _exists(db_session, User, user_id=user.user_id)


@pytest.mark.asyncio
async def test_the_run_aborts_after_three_consecutive_memory_failures(
    db_session, memory_purge
) -> None:
    owner = await make_user(db_session)
    scenario = await make_scenario(db_session, owner)
    users = [
        (await _due_user_with_playthrough(db_session, scenario, minutes=index))[0]
        for index in range(4)
    ]
    memory_purge.side_effect = MemoryPurgeError("unavailable")

    result = await _build_service(db_session).purge_expired_accounts()

    assert (result.purged, result.skipped, result.is_aborted) == (0, 3, True)
    assert memory_purge.await_count == settings.memory_purge_max_consecutive_failures
    assert await _exists(db_session, User, user_id=users[3].user_id)


@pytest.mark.asyncio
async def test_a_success_resets_the_consecutive_failure_count(
    db_session, memory_purge
) -> None:
    owner = await make_user(db_session)
    scenario = await make_scenario(db_session, owner)
    for index in range(5):
        await _due_user_with_playthrough(db_session, scenario, minutes=index)
    failure = MemoryPurgeError("unavailable")
    memory_purge.side_effect = [
        failure,
        failure,
        MemoryPurgeResult(),
        failure,
        failure,
    ]

    result = await _build_service(db_session).purge_expired_accounts()

    assert (result.purged, result.skipped, result.is_aborted) == (1, 4, False)


@pytest.mark.asyncio
async def test_only_deletable_scenarios_are_sent_to_memory(
    db_session, memory_purge
) -> None:
    user = await make_user(db_session)
    player = await make_user(db_session)
    draft = await make_scenario(db_session, user, status="draft")
    await make_scenario(db_session, user, status="published")
    played = await make_scenario(db_session, user, status="archived")
    await add_playthrough(db_session, played, player)
    user.deletion_requested_at = EXPIRED
    await db_session.flush()

    await _build_service(db_session).purge_expired_accounts()

    memory_purge.assert_awaited_once_with(scenario_ids=[draft.scenario_id])


@pytest.mark.asyncio
async def test_a_scenario_memory_failure_keeps_the_scenario_and_the_user(
    db_session, memory_purge
) -> None:
    user = await make_user(db_session)
    draft = await make_scenario(db_session, user, status="draft")
    user.deletion_requested_at = EXPIRED
    await db_session.flush()
    memory_purge.side_effect = MemoryPurgeError("unavailable")

    result = await _build_service(db_session).purge_expired_accounts()

    assert result.skipped == 1
    assert await _exists(db_session, Scenario, scenario_id=draft.scenario_id)
    assert await _exists(db_session, User, user_id=user.user_id)


@pytest.mark.asyncio
async def test_memory_is_not_called_for_a_user_with_no_playthroughs_or_scenarios(
    db_session, memory_purge
) -> None:
    user = await make_user(db_session)
    user.deletion_requested_at = EXPIRED
    await db_session.flush()

    await _build_service(db_session).purge_expired_accounts()

    memory_purge.assert_not_awaited()

from uuid import UUID, uuid4

from app.repositories import dispatch_delivery_repo
from psycopg import AsyncConnection
from strategy_contracts.agents import AgentTrait, AgentView, DispatchBriefing
from strategy_contracts.pressure import PressureBand, RumorTopic

from tests.repositories.helpers import seed_playthrough

LEASE_SECONDS = 60
MAX_ATTEMPTS = 3
NARRATION = "My lord, the border is quiet."


def _briefing(identity: UUID, rumor_id: str = "rumor_1", turn: int = 4):
    return DispatchBriefing(
        rumor_id=rumor_id,
        playthrough_id=identity,
        turn=turn,
        agent=AgentView(name="Aldous", traits=[AgentTrait.HONEST]),
        about_faction_id="house_dunwick",
        topic=RumorTopic.WILL,
        reported_band=PressureBand.HIGH,
    )


async def _seed(connection: AsyncConnection, rumor_id: str = "rumor_1") -> UUID:
    identity = await seed_playthrough(connection)
    await dispatch_delivery_repo.insert(connection, _briefing(identity, rumor_id))
    return identity


async def _claim(connection: AsyncConnection, identity: UUID, token: UUID):
    return await dispatch_delivery_repo.claim(
        connection, identity, "rumor_1", uuid4(), token, LEASE_SECONDS, MAX_ATTEMPTS
    )


async def test_insert_twice_keeps_one_row(db_connection: AsyncConnection) -> None:
    identity = await _seed(db_connection)
    await dispatch_delivery_repo.insert(db_connection, _briefing(identity))

    rows = await dispatch_delivery_repo.list_page(db_connection, identity, 10)

    assert [row.rumor_id for row in rows] == ["rumor_1"]
    assert rows[0].status == "pending"
    assert rows[0].briefing.reported_band is PressureBand.HIGH


async def test_list_page_orders_by_turn_descending(
    db_connection: AsyncConnection,
) -> None:
    identity = await _seed(db_connection)
    await dispatch_delivery_repo.insert(
        db_connection, _briefing(identity, "rumor_2", turn=9)
    )

    rows = await dispatch_delivery_repo.list_page(db_connection, identity, 10)

    assert [row.rumor_id for row in rows] == ["rumor_2", "rumor_1"]


async def test_claim_succeeds_once_until_the_lease_expires(
    db_connection: AsyncConnection,
) -> None:
    identity = await _seed(db_connection)

    first = await _claim(db_connection, identity, uuid4())
    second = await _claim(db_connection, identity, uuid4())
    await db_connection.execute(
        "UPDATE dispatch_deliveries SET lease_expires_at = now() - interval '1 second'"
    )
    third = await _claim(db_connection, identity, uuid4())

    assert first is not None and first.status == "generating"
    assert second is None
    assert third is not None and third.attempts == 2


async def test_complete_with_wrong_token_is_refused(
    db_connection: AsyncConnection,
) -> None:
    identity = await _seed(db_connection)
    await _claim(db_connection, identity, uuid4())

    is_done = await dispatch_delivery_repo.complete(
        db_connection, identity, "rumor_1", uuid4(), NARRATION
    )

    assert is_done is False


async def test_complete_stores_narration_and_blocks_further_claims(
    db_connection: AsyncConnection,
) -> None:
    identity = await _seed(db_connection)
    token = uuid4()
    await _claim(db_connection, identity, token)

    is_done = await dispatch_delivery_repo.complete(
        db_connection, identity, "rumor_1", token, NARRATION
    )
    row = await dispatch_delivery_repo.get(db_connection, identity, "rumor_1")

    assert is_done is True
    assert row is not None and row.narration == NARRATION
    assert await _claim(db_connection, identity, uuid4()) is None


async def test_fail_then_reclaim_until_attempts_cap(
    db_connection: AsyncConnection,
) -> None:
    identity = await _seed(db_connection)
    for _ in range(MAX_ATTEMPTS):
        token = uuid4()
        assert await _claim(db_connection, identity, token) is not None
        assert await dispatch_delivery_repo.fail(
            db_connection, identity, "rumor_1", token, "provider_timeout"
        )

    assert await _claim(db_connection, identity, uuid4()) is None

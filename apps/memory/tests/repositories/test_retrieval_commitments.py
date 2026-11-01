"""Eligible commitments: open or recently resolved, playthrough scope only."""

from uuid import UUID

from app.models.common import CommitmentStatusValue
from app.repositories import commitment_repo
from psycopg import AsyncConnection
from tests.repositories import helpers_retrieval as helpers

AT_SEQ = 50
RESOLUTION_TURNS = 20
LIMIT = 10


async def _eligible(
    connection: AsyncConnection,
    world: helpers.World,
    seeds: list[UUID],
    *,
    at_seq: int = AT_SEQ,
    limit: int = LIMIT,
):
    return await commitment_repo.list_eligible_commitments(
        connection,
        helpers.make_context(world, at_seq=at_seq),
        seeds,
        recent_resolution_turns=RESOLUTION_TURNS,
        limit=limit,
    )


async def _commit(
    connection: AsyncConnection,
    world: helpers.World,
    owner: UUID,
    *,
    opened_seq: int = 5,
    statuses: tuple[tuple[int, CommitmentStatusValue], ...] = (),
    counterparty: UUID | None = None,
    summary: str = "a promise",
) -> UUID:
    commitment = await helpers.add_commitment(
        connection,
        world.playthrough_id,
        owner,
        opened_seq=opened_seq,
        counterparty_entity_id=counterparty,
        summary=summary,
    )
    for at_seq, status in statuses:
        await helpers.add_commitment_status(
            connection, commitment.commitment_id, at_seq, status
        )
    return commitment.commitment_id


async def test_open_commitment_and_commitment_without_status_are_returned(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    owner = await helpers.add_entity(db_connection, world.playthrough_scope, "Mira")
    no_status = await _commit(db_connection, world, owner, summary="none")
    explicit_open = await _commit(
        db_connection, world, owner, statuses=((6, "open"),), summary="open"
    )

    rows = await _eligible(db_connection, world, [owner])

    by_id = {commitment.commitment_id: status for commitment, status in rows}
    assert set(by_id) == {no_status, explicit_open}
    assert by_id[no_status] is None
    assert by_id[explicit_open] is not None
    assert by_id[explicit_open].status == "open"


async def test_resolved_within_the_window_is_returned_with_its_status(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    owner = await helpers.add_entity(db_connection, world.playthrough_scope, "Mira")
    boundary = AT_SEQ - RESOLUTION_TURNS
    fulfilled = await _commit(
        db_connection, world, owner, statuses=((boundary, "fulfilled"),)
    )
    broken = await _commit(
        db_connection, world, owner, statuses=((boundary + 5, "broken"),)
    )
    cancelled = await _commit(
        db_connection, world, owner, statuses=((AT_SEQ, "cancelled"),)
    )

    rows = await _eligible(db_connection, world, [owner])

    statuses = {c.commitment_id: s.status for c, s in rows if s is not None}
    assert statuses == {
        fulfilled: "fulfilled",
        broken: "broken",
        cancelled: "cancelled",
    }


async def test_resolved_before_the_window_is_not_returned(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    owner = await helpers.add_entity(db_connection, world.playthrough_scope, "Mira")
    boundary = AT_SEQ - RESOLUTION_TURNS
    await _commit(db_connection, world, owner, statuses=((boundary - 1, "fulfilled"),))
    await _commit(db_connection, world, owner, statuses=((AT_SEQ - 30, "broken"),))

    assert await _eligible(db_connection, world, [owner]) == []


async def test_status_after_at_seq_is_ignored_and_reopened_commitment_is_open(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    owner = await helpers.add_entity(db_connection, world.playthrough_scope, "Mira")
    resolved_later = await _commit(
        db_connection, world, owner, statuses=((AT_SEQ + 3, "fulfilled"),)
    )
    reopened = await _commit(
        db_connection,
        world,
        owner,
        statuses=((8, "fulfilled"), (12, "open")),
    )

    rows = await _eligible(db_connection, world, [owner])

    by_id = {commitment.commitment_id: status for commitment, status in rows}
    assert set(by_id) == {resolved_later, reopened}
    assert by_id[resolved_later] is None
    assert by_id[reopened] is not None
    assert by_id[reopened].status == "open"


async def test_commitment_opened_after_at_seq_is_not_returned(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    owner = await helpers.add_entity(db_connection, world.playthrough_scope, "Mira")
    await _commit(db_connection, world, owner, opened_seq=AT_SEQ + 1)
    on_time = await _commit(db_connection, world, owner, opened_seq=AT_SEQ)

    rows = await _eligible(db_connection, world, [owner])

    assert [commitment.commitment_id for commitment, _ in rows] == [on_time]


async def test_commitment_matches_owner_or_counterparty_seed_only(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    scope = world.playthrough_scope
    mira = await helpers.add_entity(db_connection, scope, "Mira")
    bram = await helpers.add_entity(db_connection, scope, "Bram")
    cara = await helpers.add_entity(db_connection, scope, "Cara")
    owned = await _commit(db_connection, world, mira, summary="owned")
    counter = await _commit(db_connection, world, bram, counterparty=mira)
    await _commit(db_connection, world, bram, counterparty=cara)

    rows = await _eligible(db_connection, world, [mira])

    assert {commitment.commitment_id for commitment, _ in rows} == {owned, counter}
    assert await _eligible(db_connection, world, []) == []


async def test_commitments_of_other_playthroughs_never_leak(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    mira = await helpers.add_entity(db_connection, world.playthrough_scope, "Mira")
    sibling_mira = await helpers.add_entity(db_connection, world.sibling_scope, "Mira")
    mine = await _commit(db_connection, world, mira)
    await helpers.add_commitment(
        db_connection, world.sibling_playthrough_id, sibling_mira, opened_seq=5
    )
    await helpers.add_commitment(
        db_connection, world.sibling_playthrough_id, mira, opened_seq=5
    )

    rows = await _eligible(db_connection, world, [mira, sibling_mira])

    assert [commitment.commitment_id for commitment, _ in rows] == [mine]


async def test_commitments_are_ordered_by_latest_activity_and_limited(
    db_connection: AsyncConnection,
) -> None:
    world = await helpers.build_world(db_connection)
    owner = await helpers.add_entity(db_connection, world.playthrough_scope, "Mira")
    oldest = await _commit(db_connection, world, owner, opened_seq=2)
    reactivated = await _commit(
        db_connection, world, owner, opened_seq=3, statuses=((45, "fulfilled"),)
    )
    newest = await _commit(db_connection, world, owner, opened_seq=40)

    rows = await _eligible(db_connection, world, [owner])
    limited = await _eligible(db_connection, world, [owner], limit=2)

    assert [c.commitment_id for c, _ in rows] == [reactivated, newest, oldest]
    assert [c.commitment_id for c, _ in limited] == [reactivated, newest]
    assert await _eligible(db_connection, world, [owner], limit=0) == []

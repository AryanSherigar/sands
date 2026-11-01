"""Relay tests against a real test Postgres; memory's HTTP is mocked with respx."""

import asyncio
import json
import uuid

import httpx
import pytest
import respx
import structlog
from app.config import settings
from app.db.models.memory_outbox import MemoryOutbox
from app.db.models.memory_relay_claim import MemoryRelayClaim
from app.db.models.turn_log import TurnLog
from app.exceptions.memory_exceptions import MemoryIngestError
from app.integrations import memory_client
from app.services.memory_relay_service import MemoryRelayService
from memory_outbox_factories import (
    CANARY,
    add_flush,
    add_participants_row,
    add_register_row,
    add_turn,
    reload_rows,
    seed_playthrough,
)
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

pytestmark = pytest.mark.asyncio(loop_scope="session")

INGEST_URL = f"{settings.memory_url}/v1/ingest/items"


@pytest.fixture(autouse=True)
def _fresh_ingest_client(monkeypatch):
    monkeypatch.setattr(memory_client, "_client", None)
    yield
    monkeypatch.setattr(memory_client, "_client", None)


@pytest.fixture
async def relay(test_engine) -> MemoryRelayService:
    factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(delete(MemoryRelayClaim))
        await session.execute(delete(MemoryOutbox))
        await session.commit()
    return MemoryRelayService(factory)


def _ok_response(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    return httpx.Response(
        200,
        json={
            "playthrough_id": body["playthrough_id"],
            "ingested_seq": 0,
            "latest_seq_seen": 0,
            "items": [
                {
                    "item_kind": item["item_kind"],
                    "sequence": item["sequence"],
                    "outcome": "applied",
                }
                for item in body["items"]
            ],
        },
    )


async def test_delivers_register_turns_and_flush_in_order_in_one_request(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_flush(db_session, seeded, 2)
    await add_turn(db_session, seeded, 2)
    await add_turn(db_session, seeded, 1)
    await add_register_row(db_session, seeded)

    with respx.mock() as router:
        route = router.post(INGEST_URL).mock(side_effect=_ok_response)
        summary = await relay.deliver_playthrough(seeded.playthrough_id)

    assert route.call_count == 1
    body = json.loads(route.calls[0].request.content)
    assert body["playthrough_id"] == str(seeded.playthrough_id)
    assert [(i["item_kind"], i["sequence"]) for i in body["items"]] == [
        ("register_playthrough", 0),
        ("turn", 1),
        ("turn", 2),
        ("flush", 2),
    ]
    assert (summary.playthroughs_attempted, summary.rows_delivered) == (1, 4)
    rows = await reload_rows(db_session, seeded)
    assert all(row.delivered_at is not None for row in rows)
    assert all(row.last_error is None for row in rows)
    assert route.calls[0].request.headers["x-dev-service-name"] == (
        settings.memory_service_name
    )


async def test_participants_item_follows_its_turn_and_precedes_the_flush(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_flush(db_session, seeded, 1)
    await add_participants_row(db_session, seeded, 1)
    await add_turn(db_session, seeded, 1)
    await add_register_row(db_session, seeded)

    with respx.mock() as router:
        route = router.post(INGEST_URL).mock(side_effect=_ok_response)
        await relay.deliver_playthrough(seeded.playthrough_id)

    body = json.loads(route.calls[0].request.content)
    assert [(i["item_kind"], i["sequence"]) for i in body["items"]] == [
        ("register_playthrough", 0),
        ("turn", 1),
        ("participants", 1),
        ("flush", 1),
    ]
    participants_item = body["items"][2]
    assert participants_item["payload"]["participants"][0]["display_name"] == "Ada"


async def test_turn_item_carries_actor_and_rejected_calls(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    await add_turn(
        db_session,
        seeded,
        1,
        tool_calls=[
            {
                "tool_name": "set_field",
                "arguments": {"path": "x"},
                "result": {"error": "no"},
                "is_valid": False,
            },
            {
                "tool_name": "propose_check",
                "arguments": {},
                "result": {},
                "is_valid": False,
            },
        ],
        accepted_delta={
            "items": [
                {"kind": "state_mutation", "key": "gold", "before": 1, "after": 2}
            ]
        },
    )

    with respx.mock() as router:
        route = router.post(INGEST_URL).mock(side_effect=_ok_response)
        await relay.deliver_playthrough(seeded.playthrough_id)

    turn = json.loads(route.calls[0].request.content)["items"][1]["payload"]
    assert turn["participant_id"] == str(seeded.participant_id)
    assert turn["action_mode"] == "say"
    assert turn["turn_number"] == 1
    assert [call["tool_name"] for call in turn["rejected_calls"]] == ["set_field"]
    assert turn["accepted_delta"]["items"][0]["key"] == "gold"


@pytest.mark.parametrize(
    ("response", "expected_error"),
    [
        (httpx.Response(409, json={"code": "not_registered"}), "409:not_registered"),
        (
            httpx.Response(422, json={"code": "items_out_of_order"}),
            "422:items_out_of_order",
        ),
        (httpx.Response(503, text="<html>secret body</html>"), "503:unknown"),
        (httpx.Response(200, json={"unexpected": True}), "200:invalid_response"),
    ],
)
async def test_failure_leaves_rows_undelivered_and_records_a_code(
    db_session: AsyncSession,
    relay: MemoryRelayService,
    response: httpx.Response,
    expected_error: str,
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    await add_turn(db_session, seeded, 1)

    with respx.mock() as router:
        router.post(INGEST_URL).mock(return_value=response)
        summary = await relay.deliver_playthrough(seeded.playthrough_id)

    assert (summary.rows_delivered, summary.rows_failed) == (0, 2)
    rows = await reload_rows(db_session, seeded)
    assert [row.delivered_at for row in rows] == [None, None]
    assert [row.attempt_count for row in rows] == [1, 1]
    assert [row.last_error for row in rows] == [expected_error] * 2


async def test_unreachable_memory_records_unavailable_and_retries_later(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)

    with respx.mock() as router:
        router.post(INGEST_URL).mock(side_effect=httpx.ConnectError("refused"))
        await relay.deliver_playthrough(seeded.playthrough_id)
    [row] = await reload_rows(db_session, seeded)
    assert (row.delivered_at, row.attempt_count, row.last_error) == (
        None,
        1,
        "0:unavailable",
    )

    with respx.mock() as router:
        router.post(INGEST_URL).mock(side_effect=_ok_response)
        await relay.deliver_playthrough(seeded.playthrough_id)
    [row] = await reload_rows(db_session, seeded)
    assert row.delivered_at is not None


async def test_not_registered_then_registered_delivers_register_first(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_turn(db_session, seeded, 1)

    with respx.mock() as router:
        router.post(INGEST_URL).mock(
            return_value=httpx.Response(409, json={"code": "not_registered"})
        )
        await relay.deliver_playthrough(seeded.playthrough_id)
    await add_register_row(db_session, seeded)
    with respx.mock() as router:
        route = router.post(INGEST_URL).mock(side_effect=_ok_response)
        await relay.deliver_playthrough(seeded.playthrough_id)

    kinds = [
        i["item_kind"] for i in json.loads(route.calls[0].request.content)["items"]
    ]
    assert kinds == ["register_playthrough", "turn"]


async def test_duplicate_outcomes_still_mark_rows_delivered(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)

    def _duplicate(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "playthrough_id": body["playthrough_id"],
                "ingested_seq": 0,
                "latest_seq_seen": 0,
                "items": [
                    {
                        "item_kind": "register_playthrough",
                        "sequence": 0,
                        "outcome": "duplicate",
                    }
                ],
            },
        )

    with respx.mock() as router:
        router.post(INGEST_URL).mock(side_effect=_duplicate)
        await relay.deliver_playthrough(seeded.playthrough_id)

    [row] = await reload_rows(db_session, seeded)
    assert row.delivered_at is not None


async def test_missing_turn_log_is_dead_lettered_and_others_delivered(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    orphan_log, _ = await add_turn(db_session, seeded, 1)
    await add_turn(db_session, seeded, 2)
    await db_session.execute(
        delete(TurnLog).where(TurnLog.turn_id == orphan_log.turn_id)
    )
    await db_session.commit()

    with respx.mock() as router:
        route = router.post(INGEST_URL).mock(side_effect=_ok_response)
        summary = await relay.deliver_playthrough(seeded.playthrough_id)

    kinds = [
        (i["item_kind"], i["sequence"])
        for i in json.loads(route.calls[0].request.content)["items"]
    ]
    assert kinds == [("register_playthrough", 0), ("turn", 2)]
    assert summary.rows_delivered == 3
    rows = await reload_rows(db_session, seeded)
    assert [row.last_error for row in rows] == [None, "turn_log_missing", None]
    assert all(row.delivered_at is not None for row in rows)


async def test_only_orphans_pending_makes_no_http_call(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_turn(db_session, seeded, 1, participant_id=None)

    with respx.mock(assert_all_called=False) as router:
        route = router.post(INGEST_URL).mock(side_effect=_ok_response)
        await relay.deliver_playthrough(seeded.playthrough_id)

    assert route.call_count == 0
    [row] = await reload_rows(db_session, seeded)
    assert (row.delivered_at is not None, row.last_error) == (
        True,
        "participant_missing",
    )


async def test_invalid_register_payload_is_a_visible_failure_with_no_http_call(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded, payload={"scenario_id": "bad"})

    with respx.mock(assert_all_called=False) as router:
        route = router.post(INGEST_URL).mock(side_effect=_ok_response)
        summary = await relay.deliver_playthrough(seeded.playthrough_id)

    assert route.call_count == 0
    assert summary.rows_failed == 1
    [row] = await reload_rows(db_session, seeded)
    assert (row.delivered_at, row.attempt_count, row.last_error) == (
        None,
        1,
        "0:invalid_payload",
    )


async def test_batch_limit_drains_a_long_backlog_over_passes(
    db_session: AsyncSession, relay: MemoryRelayService, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "memory_relay_batch_limit", 3)
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    for turn_number in range(1, 6):
        await add_turn(db_session, seeded, turn_number)

    with respx.mock() as router:
        route = router.post(INGEST_URL).mock(side_effect=_ok_response)
        await relay.deliver_playthrough(seeded.playthrough_id)
        await relay.deliver_playthrough(seeded.playthrough_id)

    sequences = [
        [i["sequence"] for i in json.loads(call.request.content)["items"]]
        for call in route.calls
    ]
    assert sequences == [[0, 1, 2], [3, 4, 5]]


async def test_pass_with_nothing_pending_does_nothing(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)

    with respx.mock(assert_all_called=False) as router:
        route = router.post(INGEST_URL).mock(side_effect=_ok_response)
        summary = await relay.deliver_playthrough(seeded.playthrough_id)

    assert route.call_count == 0
    assert summary.model_dump() == {
        "playthroughs_attempted": 0,
        "rows_delivered": 0,
        "rows_failed": 0,
    }


async def test_a_failing_playthrough_does_not_block_the_next_one(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    first = await seed_playthrough(db_session)
    second = await seed_playthrough(db_session)
    await add_register_row(db_session, first)
    await add_register_row(db_session, second)

    def _fail_first(request: httpx.Request) -> httpx.Response:
        if json.loads(request.content)["playthrough_id"] == str(first.playthrough_id):
            return httpx.Response(500)
        return _ok_response(request)

    with respx.mock() as router:
        router.post(INGEST_URL).mock(side_effect=_fail_first)
        await relay.deliver_pending()

    assert (await reload_rows(db_session, first))[0].delivered_at is None
    assert (await reload_rows(db_session, second))[0].delivered_at is not None


async def test_concurrent_relay_cannot_deliver_rows_behind_a_held_prefix(
    db_session: AsyncSession, relay: MemoryRelayService, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "memory_relay_batch_limit", 3)
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    for turn_number in range(1, 6):
        await add_turn(db_session, seeded, turn_number)
    holding = asyncio.Event()
    release = asyncio.Event()
    sent: list[list[int]] = []

    async def _slow_ingest(request):
        sent.append([item.sequence for item in request.items])
        if len(sent) == 1:
            holding.set()
            await release.wait()
        return _response_for(request)

    monkeypatch.setattr(memory_client, "ingest_items", _slow_ingest)
    first = asyncio.create_task(relay.deliver_playthrough(seeded.playthrough_id))
    await asyncio.wait_for(holding.wait(), timeout=5)

    second_summary = await relay.deliver_playthrough(seeded.playthrough_id)
    release.set()
    await first

    assert second_summary.playthroughs_attempted == 0
    assert sent == [[0, 1, 2]]


def _response_for(request):
    from app.models.memory_ingest import IngestResponse

    return IngestResponse(
        playthrough_id=request.playthrough_id,
        ingested_seq=0,
        latest_seq_seen=0,
        items=[
            {
                "item_kind": item.item_kind,
                "sequence": item.sequence,
                "outcome": "applied",
            }
            for item in request.items
        ],
    )


async def test_two_relays_racing_deliver_every_row_exactly_once(
    db_session: AsyncSession, relay: MemoryRelayService, monkeypatch
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    for turn_number in range(1, 5):
        await add_turn(db_session, seeded, turn_number)
    sent: list[int] = []

    async def _ingest(request):
        sent.extend(item.sequence for item in request.items)
        await asyncio.sleep(0.05)
        return _response_for(request)

    monkeypatch.setattr(memory_client, "ingest_items", _ingest)

    await asyncio.gather(
        relay.deliver_playthrough(seeded.playthrough_id),
        relay.deliver_playthrough(seeded.playthrough_id),
    )

    assert sorted(sent) == [0, 1, 2, 3, 4]
    rows = await reload_rows(db_session, seeded)
    assert all(row.delivered_at is not None for row in rows)


async def test_no_player_text_reaches_logs_on_success_or_failure(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)
    await add_turn(
        db_session,
        seeded,
        1,
        tool_calls=[
            {
                "tool_name": "set_field",
                "arguments": {"path": CANARY},
                "result": {"error": CANARY},
                "is_valid": False,
            }
        ],
    )

    with structlog.testing.capture_logs() as captured, respx.mock() as router:
        router.post(INGEST_URL).mock(
            return_value=httpx.Response(500, text=f"upstream said {CANARY}")
        )
        await relay.deliver_playthrough(seeded.playthrough_id)
        router.post(INGEST_URL).mock(side_effect=_ok_response)
        await relay.deliver_playthrough(seeded.playthrough_id)

    assert captured
    assert CANARY not in json.dumps(captured, default=str)


async def test_deliver_playthrough_raises_nothing_when_memory_error_is_typed(
    db_session: AsyncSession, relay: MemoryRelayService, monkeypatch
) -> None:
    seeded = await seed_playthrough(db_session)
    await add_register_row(db_session, seeded)

    async def _raise(request):
        raise MemoryIngestError("boom", upstream_status=418)

    monkeypatch.setattr(memory_client, "ingest_items", _raise)

    await relay.deliver_playthrough(seeded.playthrough_id)

    [row] = await reload_rows(db_session, seeded)
    assert row.last_error == "418:boom"


async def test_unrelated_playthrough_rows_are_untouched(
    db_session: AsyncSession, relay: MemoryRelayService
) -> None:
    mine = await seed_playthrough(db_session)
    other = await seed_playthrough(db_session)
    await add_register_row(db_session, mine)
    await add_register_row(db_session, other)

    with respx.mock() as router:
        route = router.post(INGEST_URL).mock(side_effect=_ok_response)
        await relay.deliver_playthrough(mine.playthrough_id)

    body = json.loads(route.calls[0].request.content)
    assert body["playthrough_id"] == str(mine.playthrough_id)
    assert (await reload_rows(db_session, other))[0].delivered_at is None
    assert uuid.UUID(body["playthrough_id"]) == mine.playthrough_id

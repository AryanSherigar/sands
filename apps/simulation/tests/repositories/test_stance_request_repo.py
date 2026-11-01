from uuid import uuid4

from app.models.stance import (
    StanceBriefing,
    StanceChoice,
    StanceMenuItem,
    StanceRequest,
    StanceSource,
)
from app.repositories import stance_request_repo
from psycopg import AsyncConnection

from tests.models.builders import PLAYTHROUGH_ID
from tests.repositories.helpers import seed_playthrough

OTHER_PLAYTHROUGH_ID = uuid4()


def _choice(
    option_id: str, source: StanceSource, leader_id: str = "mira", due_turn: int = 1
) -> StanceChoice:
    return StanceChoice(
        leader_id=leader_id,
        faction_id="house_ashford",
        due_turn=due_turn,
        option_id=option_id,
        source=source,
        reason_code="fallback_default"
        if source is StanceSource.FALLBACK
        else "model_pick",
        input_hash="hash-1",
    )


def _request(
    leader_id: str = "mira",
    due_turn: int = 1,
    playthrough_id=PLAYTHROUGH_ID,
) -> StanceRequest:
    return StanceRequest(
        playthrough_id=playthrough_id,
        request_id=f"stance:{leader_id}:{due_turn}",
        leader_id=leader_id,
        faction_id="house_ashford",
        due_turn=due_turn,
        input_hash="hash-1",
        briefing=StanceBriefing(
            leader_name="Mira",
            trait_notes=[],
            ambitions=[],
            memories=[],
            opinions=[],
            current_option_id=None,
            menu=[StanceMenuItem(id="turtle", name="Turtle", description="")],
        ),
        fallback=_choice("turtle", StanceSource.FALLBACK, leader_id, due_turn),
    )


async def test_insert_is_idempotent(db_connection: AsyncConnection) -> None:
    await seed_playthrough(db_connection)
    assert await stance_request_repo.insert_request(db_connection, _request())
    assert not await stance_request_repo.insert_request(db_connection, _request())


async def test_claim_leases_pending_once(db_connection: AsyncConnection) -> None:
    await seed_playthrough(db_connection)
    await stance_request_repo.insert_request(db_connection, _request())
    claimed = await stance_request_repo.claim_requests(db_connection, uuid4(), 5)
    assert [item.request_id for item in claimed] == ["stance:mira:1"]
    assert claimed[0].lease_token is not None
    assert await stance_request_repo.claim_requests(db_connection, uuid4(), 5) == []


async def test_fallback_only_rows_are_never_claimed(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await stance_request_repo.insert_request(
        db_connection, _request(), is_fallback_only=True
    )
    assert await stance_request_repo.claim_requests(db_connection, uuid4(), 5) == []
    frozen = await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert frozen["mira"].source is StanceSource.FALLBACK


async def test_freeze_alone_does_not_block_a_late_answer(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await stance_request_repo.insert_request(db_connection, _request())
    claimed = await stance_request_repo.claim_requests(db_connection, uuid4(), 5)
    await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert await stance_request_repo.complete_request(
        db_connection,
        PLAYTHROUGH_ID,
        "stance:mira:1",
        claimed[0].lease_token,
        _choice("expand", StanceSource.MODEL),
    )


async def test_complete_after_activation_returns_false(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await stance_request_repo.insert_request(db_connection, _request())
    claimed = await stance_request_repo.claim_requests(db_connection, uuid4(), 5)
    await stance_request_repo.activate_stances(db_connection, PLAYTHROUGH_ID, 1)
    was_recorded = await stance_request_repo.complete_request(
        db_connection,
        PLAYTHROUGH_ID,
        "stance:mira:1",
        claimed[0].lease_token,
        _choice("expand", StanceSource.MODEL),
    )
    assert not was_recorded


async def test_freeze_uses_fallback_when_no_candidate(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await stance_request_repo.insert_request(db_connection, _request())
    frozen = await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert frozen == {"mira": _choice("turtle", StanceSource.FALLBACK)}


async def test_freeze_prefers_completed_candidate(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await stance_request_repo.insert_request(db_connection, _request())
    claimed = await stance_request_repo.claim_requests(db_connection, uuid4(), 5)
    model_choice = _choice("expand", StanceSource.MODEL)
    assert await stance_request_repo.complete_request(
        db_connection,
        PLAYTHROUGH_ID,
        "stance:mira:1",
        claimed[0].lease_token,
        model_choice,
    )
    frozen = await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert frozen == {"mira": model_choice}
    await stance_request_repo.activate_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert (
        await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
        == frozen
    )


async def test_failed_request_freezes_to_fallback(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await stance_request_repo.insert_request(db_connection, _request())
    claimed = await stance_request_repo.claim_requests(db_connection, uuid4(), 5)
    assert await stance_request_repo.fail_request(
        db_connection, PLAYTHROUGH_ID, "stance:mira:1", claimed[0].lease_token
    )
    frozen = await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert frozen["mira"].source is StanceSource.FALLBACK


async def test_freeze_is_per_playthrough_and_ignores_later_turns(
    db_connection: AsyncConnection,
) -> None:
    await seed_playthrough(db_connection)
    await seed_playthrough(db_connection, OTHER_PLAYTHROUGH_ID)
    await stance_request_repo.insert_request(db_connection, _request())
    await stance_request_repo.insert_request(db_connection, _request("mira", 7))
    await stance_request_repo.insert_request(
        db_connection, _request(playthrough_id=OTHER_PLAYTHROUGH_ID)
    )
    frozen = await stance_request_repo.freeze_stances(db_connection, PLAYTHROUGH_ID, 1)
    assert list(frozen) == ["mira"] and frozen["mira"].due_turn == 1
    other = await stance_request_repo.freeze_stances(
        db_connection, OTHER_PLAYTHROUGH_ID, 1
    )
    assert list(other) == ["mira"]

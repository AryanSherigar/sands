from uuid import uuid4

from app.engine.battles.policy import select_intent
from app.engine.battles.views import intent_briefing
from app.models.battle_progress import IntentRequest
from app.repositories import intent_request_repo
from psycopg import AsyncConnection

from tests.engine.battles.builders import DEFENDER, battle_fixture, start_battle
from tests.repositories.helpers import seed_playthrough


def request_fixture() -> IntentRequest:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    briefing = intent_briefing(world, world.battles[0].id, DEFENDER, scenario)
    fallback = select_intent(briefing, scenario.tuning.battle)
    return IntentRequest(
        playthrough_id=world.playthrough_id,
        request_id="intent-1",
        battle_id=fallback.battle_id,
        faction_id=fallback.faction_id,
        campaign_turn=0,
        intended_wave=1,
        input_hash=fallback.input_hash,
        observation_fingerprint=fallback.observation_fingerprint,
        policy_version=fallback.policy_version,
        redacted_input=briefing,
        fallback=fallback,
    )


async def test_claim_once_then_freeze_rejects_late_answer(
    db_connection: AsyncConnection,
) -> None:
    request = request_fixture()
    await seed_playthrough(db_connection, request.playthrough_id)
    assert await intent_request_repo.insert_request(db_connection, request)
    assert not await intent_request_repo.insert_request(db_connection, request)
    claimed = await intent_request_repo.claim_requests(db_connection, uuid4(), limit=99)
    assert len(claimed) == 1 and claimed[0].attempts == 1
    frozen = await intent_request_repo.freeze_intents(
        db_connection, request.playthrough_id, 0, 1
    )
    assert frozen[request.fallback.id] == request.fallback
    assert not await intent_request_repo.complete_request(
        db_connection,
        request.playthrough_id,
        request.request_id,
        claimed[0].lease_token,
        request.fallback,
    )
    assert await intent_request_repo.claim_requests(db_connection, uuid4()) == []


async def test_claims_enforce_global_cap_and_expired_leases_use_fallback(
    db_connection: AsyncConnection,
) -> None:
    request = request_fixture()
    await seed_playthrough(db_connection, request.playthrough_id)
    for index in range(3):
        copied = request.model_copy(
            update={
                "request_id": f"request-{index}",
                "campaign_turn": index,
                "fallback": request.fallback.model_copy(
                    update={"campaign_turn": index}
                ),
            }
        )
        await intent_request_repo.insert_request(db_connection, copied)
    claimed = await intent_request_repo.claim_requests(db_connection, uuid4(), limit=99)
    assert len(claimed) == 2
    assert await intent_request_repo.claim_requests(db_connection, uuid4()) == []
    await db_connection.execute(
        "UPDATE intent_requests SET lease_expires_at = now() - interval '1 second' WHERE state = 'leased'"
    )
    assert len(await intent_request_repo.claim_requests(db_connection, uuid4())) == 1
    cursor = await db_connection.execute(
        "SELECT count(*) FROM intent_requests WHERE state = 'fallback' AND attempts = 1"
    )
    assert await cursor.fetchone() == (2,)


async def test_provider_failure_records_fallback_without_retry(
    db_connection: AsyncConnection,
) -> None:
    request = request_fixture()
    await seed_playthrough(db_connection, request.playthrough_id)
    await intent_request_repo.insert_request(db_connection, request)
    claimed = (await intent_request_repo.claim_requests(db_connection, uuid4()))[0]

    assert await intent_request_repo.fail_request(
        db_connection,
        request.playthrough_id,
        request.request_id,
        claimed.lease_token,
    )
    assert not await intent_request_repo.fail_request(
        db_connection,
        request.playthrough_id,
        request.request_id,
        claimed.lease_token,
    )
    frozen = await intent_request_repo.freeze_intents(
        db_connection, request.playthrough_id, 0, 1
    )
    assert frozen[request.fallback.id] == request.fallback

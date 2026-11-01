"""Integration tests for POST /v1/turn/rule-check/arm, against a real test Postgres."""

import uuid

from app.db.models.participant import Participant
from app.db.models.playthrough import Playthrough
from app.db.models.scenario import Scenario
from app.db.models.user import User
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

ARM_URL = "/v1/turn/rule-check/arm"
CHECK_ID = "check-1"
UNARMED_ISSUED_AT = 1_000
WINDOW_MS = 12_000


async def _seed_unarmed_check(
    session: AsyncSession,
) -> tuple[Playthrough, Participant]:
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    session.add(
        User(user_id=user_id, display_name="Tester", auth_provider_id=str(uuid.uuid4()))
    )
    await session.flush()
    session.add(
        Scenario(
            scenario_id=scenario_id,
            creator_id=user_id,
            title="Night Desk",
            mode="master",
            complexity_tier="master",
            player_count_support="solo",
        )
    )
    await session.flush()
    playthrough = Playthrough(
        scenario_id=scenario_id,
        created_by=user_id,
        scenario_version=1,
        scenario_snapshot={},
        state={
            "_pending_check": {
                "check_id": CHECK_ID,
                "kind": "timed_choice",
                "window_ms": WINDOW_MS,
                "issued_at": UNARMED_ISSUED_AT,
                "is_armed": False,
                "resolved": None,
            }
        },
    )
    session.add(playthrough)
    await session.flush()
    participant = Participant(
        playthrough_id=playthrough.playthrough_id,
        user_id=user_id,
        role="owner",
        turn_order_position=1,
    )
    session.add(participant)
    await session.flush()
    await session.commit()
    return playthrough, participant


def _body(playthrough: Playthrough, participant: Participant, check_id: str) -> dict:
    return {
        "playthrough_id": str(playthrough.playthrough_id),
        "participant_id": str(participant.participant_id),
        "check_id": check_id,
    }


async def _arm(
    client: AsyncClient,
    playthrough: Playthrough,
    participant: Participant,
    check_id: str = CHECK_ID,
):
    return await client.post(
        ARM_URL,
        json=_body(playthrough, participant, check_id),
        headers={"x-dev-user-id": str(participant.user_id)},
    )


async def test_arming_stamps_the_window_start_from_the_server_clock(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    playthrough, participant = await _seed_unarmed_check(db_session)

    response = await _arm(async_client, playthrough, participant)

    assert response.status_code == 200
    body = response.json()
    assert body["check_id"] == CHECK_ID
    assert body["window_ms"] == WINDOW_MS
    assert body["issued_at"] > UNARMED_ISSUED_AT
    assert body["server_time_ms"] >= body["issued_at"]
    await db_session.refresh(playthrough)
    pending = playthrough.state["_pending_check"]
    assert pending["is_armed"] is True
    assert pending["issued_at"] == body["issued_at"]


async def test_arming_twice_keeps_the_first_stamp(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    playthrough, participant = await _seed_unarmed_check(db_session)

    first = await _arm(async_client, playthrough, participant)
    second = await _arm(async_client, playthrough, participant)

    assert second.status_code == 200
    assert second.json()["issued_at"] == first.json()["issued_at"]


async def test_arming_a_different_check_is_a_conflict(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    playthrough, participant = await _seed_unarmed_check(db_session)

    response = await _arm(async_client, playthrough, participant, "someone-else")

    assert response.status_code == 409


async def test_arming_requires_authentication(async_client: AsyncClient) -> None:
    response = await async_client.post(
        ARM_URL,
        json={
            "playthrough_id": str(uuid.uuid4()),
            "participant_id": str(uuid.uuid4()),
            "check_id": CHECK_ID,
        },
    )

    assert response.status_code == 401


async def test_arming_is_forbidden_for_another_user(
    async_client: AsyncClient, db_session: AsyncSession
) -> None:
    playthrough, participant = await _seed_unarmed_check(db_session)

    response = await async_client.post(
        ARM_URL,
        json=_body(playthrough, participant, CHECK_ID),
        headers={"x-dev-user-id": str(uuid.uuid4())},
    )

    assert response.status_code == 403

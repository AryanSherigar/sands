"""End-to-end run of roll/automatic_effect deltas and joiner names against the e2e stack.

Start the stack first (see docker-compose.e2e.yml). The run:
  1. seeds a published master-mode scenario through Core's own ORM (a player entity,
     a warden entity with an `hp` attribute, and a condition whose Effect C sets that
     attribute), then builds its memory template with Core's rebuild script;
  2. creates a playthrough for the owner, has a second user join it, and plays four
     turns through TRS with the stub narrator: turn 1 proposes a check, turn 2 attempts
     it, turn 3 is the owner again and turn 4 is the joiner;
  3. waits for the compose sweep to deliver everything, then asserts on memory's own
     tables: both participant names, an `automatic_effect` event and accepted fact, a
     `roll` event and accepted fact, and that POST /v1/retrieve returns them.

Any failed expectation raises. Run from apps/turn-resolution-service with its own venv:
    .venv/bin/python scripts/memory_delta_e2e.py
"""

import asyncio
import json
import subprocess
import uuid

import asyncpg
import httpx
from memory_outbox_e2e import (
    CORE_URL,
    INDEX_TIMEOUT_SECONDS,
    INGEST_TIMEOUT_SECONDS,
    MEMORY_DSN,
    MEMORY_URL,
    TRS_URL,
    TURN_TIMEOUT_SECONDS,
    create_playthrough,
    wait_for_stack,
    wait_for_watermark,
)

CORE_CONTAINER = "sands-e2e-core-api"
OWNER_NAME = "Ada"
JOINER_NAME = "Bram"
WARDEN_HP = 7
TURN_COUNT = 4
CHECK_DIFFICULTY = 12
JOIN_TOKEN_PREFIX = "e2e-join-"

SEED_SCRIPT = """
import asyncio, json, uuid
from datetime import UTC, datetime, timedelta
from app.db.connection import close_db_connection, get_session_factory
from app.db.models.entity import Entity
from app.db.models.scenario import Scenario
from app.db.models.scenario_condition import ScenarioCondition
from app.db.models.user import User

OWNER, JOINER, HP = "%(owner)s", "%(joiner)s", %(hp)d


async def main():
    ids = {k: str(uuid.uuid4()) for k in ("owner", "joiner", "scenario", "player", "warden")}
    async with get_session_factory()() as session:
        for key, name in (("owner", OWNER), ("joiner", JOINER)):
            session.add(User(user_id=uuid.UUID(ids[key]), display_name=name,
                             auth_provider_id="e2e-" + ids[key]))
        await session.flush()
        session.add(Scenario(
            scenario_id=uuid.UUID(ids["scenario"]), creator_id=uuid.UUID(ids["owner"]),
            title="Warden Deltas", mode="master", complexity_tier="master",
            player_count_support="both", status="published",
            published_at=datetime.now(UTC), narrator_persona="A watchful narrator."))
        await session.flush()
        session.add(Entity(entity_id=uuid.UUID(ids["player"]), scenario_id=uuid.UUID(ids["scenario"]),
                           entity_type="character", canonical_name="Kestrel", is_player=True))
        session.add(Entity(entity_id=uuid.UUID(ids["warden"]), scenario_id=uuid.UUID(ids["scenario"]),
                           entity_type="character", canonical_name="Warden Mira",
                           attributes_schema={"hp": {"type": "number", "min": 0, "max": 100}}))
        await session.flush()
        session.add(ScenarioCondition(
            scenario_id=uuid.UUID(ids["scenario"]), label="Old wound",
            condition_expression={"field": "narrative.opening_prompt", "op": "==", "value": None},
            narrator_instruction="The warden favours her left side.",
            state_mutation={"path": ids["warden"] + ".hp", "op": "set", "value": HP}))
        await session.commit()
    await close_db_connection()
    print(json.dumps(ids))

asyncio.run(main())
"""

SHARE_SCRIPT = """
import asyncio
from datetime import UTC, datetime, timedelta
from app.db.connection import close_db_connection, get_session_factory
from app.db.models.share import PlaythroughShare


async def main():
    async with get_session_factory()() as session:
        session.add(PlaythroughShare(playthrough_id="%(playthrough)s", share_token="%(token)s",
                                     mode="join", expires_at=datetime.now(UTC) + timedelta(days=1)))
        await session.commit()
    await close_db_connection()

asyncio.run(main())
"""


def run_in_core(script: str) -> str:
    result = subprocess.run(
        ["docker", "exec", "-i", CORE_CONTAINER, "python", "-"],
        input=script,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""


def run_rebuild() -> str:
    result = subprocess.run(
        [
            "docker",
            "exec",
            CORE_CONTAINER,
            "python",
            "-m",
            "scripts.rebuild_memory_templates",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout + result.stderr


async def post_turn(
    client: httpx.AsyncClient,
    user_id: str,
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    **fields: object,
) -> list[str]:
    events: list[str] = []
    body = {
        "playthrough_id": str(playthrough_id),
        "participant_id": str(participant_id),
        "client_action_id": str(uuid.uuid4()),
        "action_text": "",
        "action_mode": "do",
        **fields,
    }
    async with client.stream(
        "POST",
        f"{TRS_URL}/v1/turn",
        json=body,
        headers={"x-dev-user-id": user_id},
        timeout=TURN_TIMEOUT_SECONDS,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
    assert events and events[-1] == "done", f"turn events: {events}"
    return events


async def play_four_turns(
    client: httpx.AsyncClient,
    ids: dict[str, str],
    playthrough_id: uuid.UUID,
    owner_participant: uuid.UUID,
    joiner_participant: uuid.UUID,
) -> None:
    first = await post_turn(
        client,
        ids["owner"],
        playthrough_id,
        owner_participant,
        action_text="I study the old lock.",
    )
    assert "check" in first, first
    pending = await pending_check_id(playthrough_id)
    attempt = await post_turn(
        client,
        ids["owner"],
        playthrough_id,
        owner_participant,
        action_kind="check_resolution",
        check_resolution={"check_id": pending, "resolution": "attempt"},
    )
    assert "check_resolved" in attempt, attempt
    await post_turn(
        client,
        ids["owner"],
        playthrough_id,
        owner_participant,
        action_text="I step back and wait.",
    )
    await post_turn(
        client,
        ids["joiner"],
        playthrough_id,
        joiner_participant,
        action_text="Bram greets the warden.",
    )


async def pending_check_id(playthrough_id: uuid.UUID) -> str:
    from memory_outbox_e2e import APP_DSN

    connection = await asyncpg.connect(APP_DSN)
    try:
        state = await connection.fetchval(
            "SELECT state FROM playthroughs WHERE playthrough_id = $1", playthrough_id
        )
    finally:
        await connection.close()
    return json.loads(state)["_pending_check"]["check_id"]


async def memory_facts(playthrough_id: uuid.UUID) -> dict[str, list[asyncpg.Record]]:
    connection = await asyncpg.connect(MEMORY_DSN)
    try:
        participants = await connection.fetchval(
            "SELECT participants FROM memory_playthrough WHERE playthrough_id = $1",
            playthrough_id,
        )
        events = await connection.fetch(
            "SELECT event_kind, event_key, is_accepted FROM memory_event"
            " WHERE playthrough_id = $1 ORDER BY sequence",
            playthrough_id,
        )
        facts = await connection.fetch(
            "SELECT predicate, object_literal, authority, assertion FROM memory_fact"
            " WHERE scope_kind = 'playthrough' AND scope_id = $1",
            playthrough_id,
        )
    finally:
        await connection.close()
    return {"participants": json.loads(participants), "events": events, "facts": facts}


async def wait_for_participants(playthrough_id: uuid.UUID) -> dict[str, list]:
    deadline = INGEST_TIMEOUT_SECONDS
    for _ in range(deadline):
        found = await memory_facts(playthrough_id)
        names = {item["display_name"] for item in found["participants"]}
        if {OWNER_NAME, JOINER_NAME} <= names and len(found["events"]) >= 2:
            return found
        await asyncio.sleep(1)
    raise TimeoutError(
        f"memory never reflected both participants: {found['participants']}"
    )


def assert_memory_state(
    ids: dict[str, str], found: dict[str, list]
) -> dict[str, object]:
    names = {item["display_name"] for item in found["participants"]}
    assert names == {OWNER_NAME, JOINER_NAME}, names
    kinds = {(row["event_kind"], row["event_key"]) for row in found["events"]}
    assert ("automatic_effect", f"{ids['warden']}.hp") in kinds, kinds
    assert any(kind == "roll" for kind, _ in kinds), kinds
    hp_facts = [f for f in found["facts"] if f["predicate"] == "hp"]
    assert [f["object_literal"] for f in hp_facts] == [str(WARDEN_HP)], hp_facts
    assert hp_facts[0]["authority"] == "accepted"
    check_facts = [f for f in found["facts"] if f["predicate"] == "check_result"]
    assert len(check_facts) == 1 and "rolled" in check_facts[0]["object_literal"], (
        check_facts
    )
    return {
        "participants": sorted(names),
        "roll_fact": check_facts[0]["object_literal"],
    }


async def retrieve_items(
    client: httpx.AsyncClient, playthrough_id: uuid.UUID, participant_id: uuid.UUID
) -> list[dict[str, object]]:
    response = await client.post(
        f"{MEMORY_URL}/v1/retrieve",
        json={
            "playthrough_id": str(playthrough_id),
            "sequence": TURN_COUNT + 1,
            "action_text": "How is Warden Mira's hp, and did Kestrel pass the lockpicking check?",
            "action_mode": "say",
            "actor_participant_id": str(participant_id),
            "recent_text": "",
            "recent_window_turns": 6,
        },
    )
    response.raise_for_status()
    return response.json()["items"]


async def main() -> None:
    async with httpx.AsyncClient(timeout=30) as client:
        await wait_for_stack(client)
        ids = json.loads(
            run_in_core(
                SEED_SCRIPT
                % {"owner": OWNER_NAME, "joiner": JOINER_NAME, "hp": WARDEN_HP}
            )
        )
        rebuild = run_rebuild()
        assert "built" in rebuild, rebuild
        owner_id = uuid.UUID(ids["owner"])
        playthrough_id, owner_participant = await create_playthrough(
            client, owner_id, uuid.UUID(ids["scenario"])
        )
        token = JOIN_TOKEN_PREFIX + uuid.uuid4().hex[:8]
        run_in_core(SHARE_SCRIPT % {"playthrough": playthrough_id, "token": token})
        joined = await client.post(
            f"{CORE_URL}/v1/playthroughs/join",
            json={"share_token": token},
            headers={"x-dev-user-id": ids["joiner"]},
        )
        joined.raise_for_status()
        joiner_participant = uuid.UUID(joined.json()["participant_id"])
        await play_four_turns(
            client, ids, playthrough_id, owner_participant, joiner_participant
        )
        await wait_for_watermark(
            playthrough_id, "ingested_seq", TURN_COUNT, INGEST_TIMEOUT_SECONDS
        )
        found = await wait_for_participants(playthrough_id)
        report = assert_memory_state(ids, found)
        await wait_for_watermark(
            playthrough_id, "indexed_seq", TURN_COUNT, INDEX_TIMEOUT_SECONDS
        )
        items = await retrieve_items(client, playthrough_id, owner_participant)
        report["retrieved_item_count"] = len(items)
        report["retrieved_texts"] = [str(item.get("text", ""))[:80] for item in items]
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    asyncio.run(main())

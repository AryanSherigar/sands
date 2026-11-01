"""End-to-end run of the memory outbox path against the isolated e2e compose stack.

Start the stack first (see docker-compose.e2e.yml). The run creates one
playthrough through Core, plays TURN_COUNT turns through TRS with a stubbed
narrator, and then waits for the compose sweep to deliver and index them. It
asserts on memory's own state and on POST /v1/retrieve, and prints a JSON
report of what it measured. Any failed expectation raises.

Run from apps/turn-resolution-service with its own venv:
    .venv/bin/python scripts/memory_outbox_e2e.py
"""

import asyncio
import json
import time
import uuid

import asyncpg
import httpx
from app.db.models.scenario import Scenario
from app.db.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

CORE_URL = "http://127.0.0.1:18000"
TRS_URL = "http://127.0.0.1:18001"
MEMORY_URL = "http://127.0.0.1:18080"
APP_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@127.0.0.1:15432/sands_db"
APP_DSN = "postgresql://postgres:postgres@127.0.0.1:15432/sands_db"
MEMORY_DSN = "postgresql://memory_db:memory_db@127.0.0.1:15433/memory_db"

TURN_COUNT = 12
SEARCH_MARKER = "zephyrine"
DEFAULT_RECENT_WINDOW_TURNS = 6
STACK_READY_TIMEOUT_SECONDS = 180
INGEST_TIMEOUT_SECONDS = 90
INDEX_TIMEOUT_SECONDS = 120
POLL_INTERVAL_SECONDS = 1.0
TURN_TIMEOUT_SECONDS = 60


async def wait_for_stack(client: httpx.AsyncClient) -> None:
    deadline = time.monotonic() + STACK_READY_TIMEOUT_SECONDS
    for name, url in (
        ("core", f"{CORE_URL}/health"),
        ("trs", f"{TRS_URL}/health"),
        ("memory", f"{MEMORY_URL}/health"),
    ):
        while True:
            try:
                if (await client.get(url)).status_code == 200:
                    break
            # NOTE: The stack is still starting; retry until the deadline below.
            except httpx.TransportError:
                pass
            if time.monotonic() > deadline:
                raise TimeoutError(f"{name} did not become healthy")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


async def seed_creator_and_scenario() -> tuple[uuid.UUID, uuid.UUID]:
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    engine = create_async_engine(APP_DATABASE_URL)
    async with AsyncSession(engine) as session:
        session.add(
            User(
                user_id=user_id,
                display_name="E2E Player",
                auth_provider_id=f"e2e-{user_id}",
            )
        )
        await session.flush()
        session.add(
            Scenario(
                scenario_id=scenario_id,
                creator_id=user_id,
                title="Harrowmere",
                mode="newbie",
                complexity_tier="newbie",
                player_count_support="solo",
                status="published",
                narrator_persona="A quiet archivist.",
                world_data={"lore": "A drowned library."},
            )
        )
        await session.commit()
    await engine.dispose()
    return user_id, scenario_id


async def create_playthrough(
    client: httpx.AsyncClient, user_id: uuid.UUID, scenario_id: uuid.UUID
) -> tuple[uuid.UUID, uuid.UUID]:
    response = await client.post(
        f"{CORE_URL}/v1/playthroughs",
        json={"scenario_id": str(scenario_id), "setup_values": {}},
        headers={"x-dev-user-id": str(user_id)},
    )
    response.raise_for_status()
    body = response.json()
    return uuid.UUID(body["playthrough_id"]), uuid.UUID(body["participant_id"])


async def play_turn(
    client: httpx.AsyncClient,
    user_id: uuid.UUID,
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    turn_number: int,
) -> float:
    started = time.monotonic()
    events: list[str] = []
    async with client.stream(
        "POST",
        f"{TRS_URL}/v1/turn",
        json={
            "playthrough_id": str(playthrough_id),
            "participant_id": str(participant_id),
            "client_action_id": str(uuid.uuid4()),
            "action_text": f"I ask the archivist about lantern number {turn_number}.",
            "action_mode": "say",
        },
        headers={"x-dev-user-id": str(user_id)},
        timeout=TURN_TIMEOUT_SECONDS,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                events.append(line.split(":", 1)[1].strip())
    assert events and events[-1] == "done", f"turn {turn_number} events: {events}"
    return time.monotonic() - started


async def outbox_state(playthrough_id: uuid.UUID) -> dict[str, object]:
    connection = await asyncpg.connect(APP_DSN)
    try:
        rows = await connection.fetch(
            "SELECT item_kind, sequence, delivered_at IS NOT NULL AS is_delivered,"
            " attempt_count, last_error FROM memory_outbox"
            " WHERE playthrough_id = $1 ORDER BY sequence, outbox_id",
            playthrough_id,
        )
    finally:
        await connection.close()
    return {
        "rows": len(rows),
        "kinds": sorted({row["item_kind"] for row in rows}),
        "delivered": sum(1 for row in rows if row["is_delivered"]),
        "with_error": sum(1 for row in rows if row["last_error"]),
        "max_attempts": max((row["attempt_count"] for row in rows), default=0),
    }


async def memory_watermarks(playthrough_id: uuid.UUID) -> dict[str, int] | None:
    connection = await asyncpg.connect(MEMORY_DSN)
    try:
        row = await connection.fetchrow(
            "SELECT ingested_seq, indexed_seq, latest_seq_seen, template_id"
            " FROM memory_playthrough WHERE playthrough_id = $1",
            playthrough_id,
        )
    finally:
        await connection.close()
    return dict(row) if row else None


async def wait_for_watermark(
    playthrough_id: uuid.UUID, column: str, target: int, timeout_seconds: float
) -> float | None:
    started = time.monotonic()
    while time.monotonic() - started < timeout_seconds:
        marks = await memory_watermarks(playthrough_id)
        if marks and marks[column] >= target:
            return time.monotonic() - started
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
    return None


async def retrieve(
    client: httpx.AsyncClient,
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    recent_window_turns: int,
) -> dict[str, object]:
    response = await client.post(
        f"{MEMORY_URL}/v1/retrieve",
        json={
            "playthrough_id": str(playthrough_id),
            "sequence": TURN_COUNT + 1,
            "action_text": f"what does the archivist say about the {SEARCH_MARKER} lantern",
            "action_mode": "say",
            "actor_participant_id": str(participant_id),
            "recent_text": "",
            "recent_window_turns": recent_window_turns,
        },
    )
    response.raise_for_status()
    return response.json()


async def probe_embedding_step(client: httpx.AsyncClient) -> str:
    response = await client.post(f"{MEMORY_URL}/v1/jobs/process-pending")
    response.raise_for_status()
    return response.json()["embedding_step"]


async def main() -> None:
    report: dict[str, object] = {}
    async with httpx.AsyncClient(timeout=30) as client:
        await wait_for_stack(client)
        user_id, scenario_id = await seed_creator_and_scenario()
        playthrough_id, participant_id = await create_playthrough(
            client, user_id, scenario_id
        )
        registered = await outbox_state(playthrough_id)
        assert registered["kinds"] == ["register_playthrough"], registered
        report["after_creation"] = registered

        durations = [
            await play_turn(client, user_id, playthrough_id, participant_id, turn)
            for turn in range(1, TURN_COUNT + 1)
        ]
        report["turn_seconds_median"] = round(sorted(durations)[len(durations) // 2], 3)
        report["turn_seconds_max"] = round(max(durations), 3)
        report["after_turns"] = await outbox_state(playthrough_id)
        assert report["after_turns"]["rows"] == TURN_COUNT + 1, report["after_turns"]

        ingested_after = await wait_for_watermark(
            playthrough_id, "ingested_seq", TURN_COUNT, INGEST_TIMEOUT_SECONDS
        )
        marks = await memory_watermarks(playthrough_id)
        assert ingested_after is not None, f"ingested_seq never reached: {marks}"
        report["ingested_after_seconds"] = round(ingested_after, 1)
        report["memory_template_id"] = str(marks["template_id"])

        final_outbox = await outbox_state(playthrough_id)
        assert final_outbox["delivered"] == TURN_COUNT + 1, final_outbox
        report["after_delivery"] = final_outbox

        embedding_step = await probe_embedding_step(client)
        report["embedding_step"] = embedding_step
        if embedding_step == "unconfigured":
            report["indexed_seq"] = "not verified: no EMBEDDING_API_KEY in this run"
        else:
            indexed_after = await wait_for_watermark(
                playthrough_id, "indexed_seq", TURN_COUNT, INDEX_TIMEOUT_SECONDS
            )
            report["indexed_after_seconds"] = (
                round(indexed_after, 1) if indexed_after is not None else None
            )
            assert indexed_after is not None, await memory_watermarks(playthrough_id)

        everything = await retrieve(client, playthrough_id, participant_id, 0)
        windowed = await retrieve(
            client, playthrough_id, participant_id, DEFAULT_RECENT_WINDOW_TURNS
        )
        span_sequences = sorted({item["sequence"] for item in everything["items"]})
        windowed_sequences = sorted({item["sequence"] for item in windowed["items"]})
        assert span_sequences, "retrieval with no window returned nothing"
        assert any(SEARCH_MARKER in item["text"] for item in everything["items"])
        latest_allowed = TURN_COUNT + 1 - DEFAULT_RECENT_WINDOW_TURNS
        assert all(seq <= latest_allowed for seq in windowed_sequences), (
            windowed_sequences
        )
        report["retrieve_no_window"] = {
            "items": len(everything["items"]),
            "sequences": span_sequences,
            "degraded_reasons": everything["degraded_reasons"],
            "skipped_branches": everything["skipped_branches"],
        }
        report["retrieve_default_window"] = {
            "items": len(windowed["items"]),
            "sequences": windowed_sequences,
        }
        report["final_watermarks"] = await memory_watermarks(playthrough_id)
        report["final_watermarks"]["template_id"] = str(
            report["final_watermarks"]["template_id"]
        )
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

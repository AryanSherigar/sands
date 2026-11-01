"""End-to-end run of the TRS memory read path against the isolated e2e compose stack.

Start the stack first (see docker-compose.e2e.yml). The run:
  1. seeds a published newbie scenario with lore and a story card, then builds its
     memory template with Core's rebuild script (run twice: the second is a no-op);
  2. plays a first turn before the playthrough is registered in memory (sweep
     stopped), expecting the bounded lore fallback in the narrator prompt;
  3. lets the sweep register it, plays a second turn, and expects recalled lore and
     the matching story card in the prompt and no inlined lore;
  4. replays the second turn's client_action_id and expects no second narration;
  5. stops memory, plays a third turn, and expects it to complete on the fallback;
  6. reports retrieve latency as seen by TRS (report only, see the sub-spec).

It asserts on the prompts recorded by the stub narrator (GET /__e2e/prompts), so a
failed expectation raises. Uses `docker` for the rebuild script and to stop and
start containers, and reuses helpers from memory_outbox_e2e.py.

Run from apps/turn-resolution-service with its own venv:
    .venv/bin/python scripts/memory_read_path_e2e.py
"""

import asyncio
import json
import statistics
import subprocess
import time
import uuid
from datetime import UTC, datetime

import asyncpg
import httpx
from app.db.models.scenario import Scenario
from app.db.models.user import User
from memory_outbox_e2e import (
    APP_DATABASE_URL,
    APP_DSN,
    MEMORY_DSN,
    MEMORY_URL,
    POLL_INTERVAL_SECONDS,
    TRS_URL,
    create_playthrough,
    memory_watermarks,
    wait_for_stack,
    wait_for_watermark,
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

CORE_CONTAINER = "sands-e2e-core-api"
TRS_CONTAINER = "sands-e2e-trs"
MEMORY_CONTAINER = "sands-e2e-memory"
SWEEP_CONTAINER = "sands-e2e-memory-sweep"
LORE_MARKER = "ashfordforge"
CARD_SENTENCE = "Mara Voss keeps the ember-glass ledger."
WORLD_LORE = (
    "The Harrowmere archive was drowned a century ago.\n\n"
    f"The {LORE_MARKER} supplies brass lanterns to the city watch."
)
TURN_TIMEOUT_SECONDS = 60
MEMORY_READY_TIMEOUT_SECONDS = 90
REGISTER_TIMEOUT_SECONDS = 60
LATENCY_SAMPLES = 60


def docker(*arguments: str) -> str:
    result = subprocess.run(
        ["docker", *arguments], capture_output=True, text=True, check=True
    )
    return result.stdout + result.stderr


async def seed_scenario() -> tuple[uuid.UUID, uuid.UUID]:
    user_id, scenario_id = uuid.uuid4(), uuid.uuid4()
    engine = create_async_engine(APP_DATABASE_URL)
    async with AsyncSession(engine) as session:
        session.add(
            User(
                user_id=user_id,
                display_name="E2E Reader",
                auth_provider_id=f"e2e-{user_id}",
            )
        )
        await session.flush()
        session.add(
            Scenario(
                scenario_id=scenario_id,
                creator_id=user_id,
                title="Harrowmere Read Path",
                mode="newbie",
                complexity_tier="newbie",
                player_count_support="solo",
                status="published",
                published_at=datetime.now(UTC),
                narrator_persona="A quiet archivist.",
                world_data={
                    "worldLore": WORLD_LORE,
                    "mainConflict": "The archive is sinking.",
                    "openingPrompt": "You wake in the flooded reading room.",
                    "storyCards": [
                        {
                            "id": "card-mara",
                            "type": "Character",
                            "name": "Mara Voss",
                            "content": CARD_SENTENCE,
                        }
                    ],
                },
            )
        )
        await session.commit()
    await engine.dispose()
    return user_id, scenario_id


def run_rebuild() -> str:
    return docker(
        "exec", CORE_CONTAINER, "python", "-m", "scripts.rebuild_memory_templates"
    )


async def template_rows(scenario_id: uuid.UUID) -> list[asyncpg.Record]:
    connection = await asyncpg.connect(MEMORY_DSN)
    try:
        return await connection.fetch(
            "SELECT publish_revision, direct_status FROM memory_template"
            " WHERE scenario_id = $1",
            scenario_id,
        )
    finally:
        await connection.close()


async def core_state(scenario_id: uuid.UUID, playthrough_id: uuid.UUID) -> dict:
    connection = await asyncpg.connect(APP_DSN)
    try:
        revision = await connection.fetchval(
            "SELECT publish_revision FROM scenarios WHERE scenario_id = $1",
            scenario_id,
        )
        turn_count = await connection.fetchval(
            "SELECT turn_count FROM playthroughs WHERE playthrough_id = $1",
            playthrough_id,
        )
        registered_revision = await connection.fetchval(
            "SELECT payload->>'publish_revision' FROM memory_outbox"
            " WHERE playthrough_id = $1 AND item_kind = 'register_playthrough'",
            playthrough_id,
        )
    finally:
        await connection.close()
    return {
        "scenario_revision": revision,
        "turn_count": turn_count,
        "registered_revision": registered_revision,
    }


async def play_turn(
    client: httpx.AsyncClient,
    user_id: uuid.UUID,
    playthrough_id: uuid.UUID,
    participant_id: uuid.UUID,
    client_action_id: uuid.UUID,
    action_text: str,
) -> list[tuple[str, str]]:
    events: list[tuple[str, str]] = []
    pending_event = ""
    async with client.stream(
        "POST",
        f"{TRS_URL}/v1/turn",
        json={
            "playthrough_id": str(playthrough_id),
            "participant_id": str(participant_id),
            "client_action_id": str(client_action_id),
            "action_text": action_text,
            "action_mode": "say",
        },
        headers={"x-dev-user-id": str(user_id)},
        timeout=TURN_TIMEOUT_SECONDS,
    ) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if line.startswith("event:"):
                pending_event = line.split(":", 1)[1].strip()
            elif line.startswith("data:") and pending_event:
                events.append((pending_event, line.split(":", 1)[1].strip()))
                pending_event = ""
    assert events and events[-1][0] == "done", f"events: {events}"
    return events


async def recorded_prompts(client: httpx.AsyncClient) -> list[dict[str, str]]:
    response = await client.get(f"{TRS_URL}/__e2e/prompts")
    response.raise_for_status()
    return response.json()


async def wait_until(condition, timeout_seconds: float, description: str) -> None:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if await condition():
            return
        await asyncio.sleep(POLL_INTERVAL_SECONDS)
    raise TimeoutError(description)


def trs_retrieve_durations_ms() -> list[float]:
    durations: list[float] = []
    for line in docker("logs", TRS_CONTAINER).splitlines():
        if '"context_retrieval"' not in line or "duration_ms" not in line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("step_name") == "context_retrieval":
            durations.append(float(record["duration_ms"]))
    return durations


async def measure_retrieve_latency(
    client: httpx.AsyncClient, playthrough_id: uuid.UUID, participant_id: uuid.UUID
) -> dict[str, float]:
    samples: list[float] = []
    for _ in range(LATENCY_SAMPLES):
        started = time.monotonic()
        response = await client.post(
            f"{MEMORY_URL}/v1/retrieve",
            json={
                "playthrough_id": str(playthrough_id),
                "sequence": 2,
                "action_text": f"I ask Mara Voss about the {LORE_MARKER}",
                "action_mode": "say",
                "actor_participant_id": str(participant_id),
                "recent_text": "Player: hello\nNarrator: hi",
                "recent_window_turns": 6,
            },
        )
        response.raise_for_status()
        samples.append((time.monotonic() - started) * 1000)
    ordered = sorted(samples)
    return {
        "p50_ms": round(statistics.median(ordered), 1),
        "p95_ms": round(ordered[int(0.95 * len(ordered)) - 1], 1),
        "max_ms": round(ordered[-1], 1),
    }


async def main() -> None:
    report: dict[str, object] = {}
    async with httpx.AsyncClient(timeout=30) as client:
        await wait_for_stack(client)
        user_id, scenario_id = await seed_scenario()

        first_output = run_rebuild()
        assert "built" in first_output, first_output
        second_output = run_rebuild()
        assert "unchanged" in second_output, second_output
        templates = await template_rows(scenario_id)
        assert [(t["publish_revision"], t["direct_status"]) for t in templates] == [
            (1, "ready")
        ], templates
        report["templates"] = [dict(row) for row in templates]

        docker("stop", SWEEP_CONTAINER)
        playthrough_id, participant_id = await create_playthrough(
            client, user_id, scenario_id
        )
        state = await core_state(scenario_id, playthrough_id)
        assert state["scenario_revision"] == 1, state
        assert state["registered_revision"] == "1", state
        assert await memory_watermarks(playthrough_id) is None

        first_events = await play_turn(
            client,
            user_id,
            playthrough_id,
            participant_id,
            uuid.uuid4(),
            "I look around the flooded room.",
        )
        first_narration = first_events[0][1][:40]
        first_prompt = (await recorded_prompts(client))[-1]["prompt"]
        assert "## Setting" in first_prompt and LORE_MARKER in first_prompt
        assert "## Story Memory" not in first_prompt
        report["turn_1"] = "unregistered: lore fallback used"

        docker("start", SWEEP_CONTAINER)

        async def is_registered_and_delivered() -> bool:
            marks = await memory_watermarks(playthrough_id)
            return bool(marks and marks["ingested_seq"] >= 1)

        await wait_until(
            is_registered_and_delivered, REGISTER_TIMEOUT_SECONDS, "registration"
        )

        second_action = uuid.uuid4()
        second_events = await play_turn(
            client,
            user_id,
            playthrough_id,
            participant_id,
            second_action,
            f"I ask Mara Voss about the {LORE_MARKER} lanterns.",
        )
        prompts = await recorded_prompts(client)
        second_prompt = prompts[-1]["prompt"]
        assert "## Story Memory" in second_prompt, second_prompt
        assert LORE_MARKER in second_prompt.split("## Story Memory", 1)[1]
        assert "## Setting" not in second_prompt
        assert "worldLore" not in second_prompt
        assert "drowned a century ago" not in second_prompt
        assert f"**Mara Voss** (Character): {CARD_SENTENCE}" in second_prompt
        memory_block = second_prompt.split("## Story Memory", 1)[1].split("</memory>")[
            0
        ]
        assert first_narration not in memory_block, "an in-window turn was recalled"
        assert first_narration in second_prompt.split("</memory>", 1)[1]
        report["turn_2"] = "recalled lore and active card; no inlined lore"

        prompt_count = len(prompts)
        replay = await play_turn(
            client,
            user_id,
            playthrough_id,
            participant_id,
            second_action,
            f"I ask Mara Voss about the {LORE_MARKER} lanterns.",
        )
        assert [name for name, _ in replay] == ["narration", "done"], replay
        assert replay[0][1] == second_events[0][1] or replay[0][1], replay
        assert len(await recorded_prompts(client)) == prompt_count
        state = await core_state(scenario_id, playthrough_id)
        assert state["turn_count"] == 2, state
        report["replay"] = "no second narration, turn_count stays 2"

        docker("stop", MEMORY_CONTAINER)
        try:
            await play_turn(
                client,
                user_id,
                playthrough_id,
                participant_id,
                uuid.uuid4(),
                "I keep talking to the archivist.",
            )
        finally:
            docker("start", MEMORY_CONTAINER)
        third_prompt = (await recorded_prompts(client))[-1]["prompt"]
        assert "## Setting" in third_prompt and "## Story Memory" not in third_prompt
        report["turn_3"] = "memory stopped: turn completed on lore fallback"

        await wait_for_stack(client)
        await wait_for_watermark(playthrough_id, "ingested_seq", 3, 90)
        report["retrieve_latency_direct"] = await measure_retrieve_latency(
            client, playthrough_id, participant_id
        )
        trs_durations = trs_retrieve_durations_ms()
        report["retrieve_seen_by_trs_ms"] = {
            "samples": len(trs_durations),
            "values": [round(value, 1) for value in trs_durations],
        }
    print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())

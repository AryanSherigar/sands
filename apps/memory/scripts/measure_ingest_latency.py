"""Measure ingest service latency on the test database.

Usage:
    python -m scripts.measure_ingest_latency     (from apps/memory/)
    python scripts/measure_ingest_latency.py     (from apps/memory/)

Sends 50 sequential turn requests and reports p50, p95, max latency in ms.
"""

import asyncio
import random
import sys
import time
from statistics import median
from uuid import UUID, uuid4

from app.config import get_settings
from app.db.migrate import apply_migrations
from app.models.ingest import (
    AcceptedDelta,
    AcceptedDeltaItem,
    RejectedCall,
    TurnPayload,
)
from app.services.ingest_service import IngestService
from psycopg import AsyncConnection

NARRATION_WORDS = [
    "The",
    "brave",
    "adventurer",
    "stood",
    "at",
    "the",
    "crossroads,",
    "facing",
    "a",
    "moment",
    "of",
    "profound",
    "uncertainty.",
    "The",
    "path",
    "ahead",
    "shimmered",
    "with",
    "ancient",
    "magic.",
    "Shadows",
    "danced",
    "across",
    "the",
    "stone",
    "walls.",
    "A",
    "cool",
    "breeze",
    "whispered",
    "secrets",
    "of",
    "forgotten",
    "kingdoms.",
    "The",
    "ground",
    "trembled",
    "slightly,",
    "as",
    "if",
    "responding",
    "to",
    "unseen",
    "forces.",
]

WORD_SEED = 42
TURN_COUNT = 50
ACTION_TEXT = "The hero readies their weapon."
REJECTED_TOOL_NAME = "cast_spell"


def _generate_narration() -> str:
    random.seed(WORD_SEED)
    words_per_paragraph = 10
    paragraph_count = random.randint(3, 5)
    paragraphs = []
    for _ in range(paragraph_count):
        paragraph_words = random.choices(NARRATION_WORDS, k=words_per_paragraph)
        paragraphs.append(" ".join(paragraph_words))
    return "\n".join(paragraphs)


def _build_hp_path() -> str:
    entity_id = uuid4()
    return f"{entity_id}.hp"


def _build_accepted_deltas() -> list[AcceptedDeltaItem]:
    return [
        AcceptedDeltaItem(kind="state_mutation", key=_build_hp_path(), after=100),
        AcceptedDeltaItem(kind="roll", key="initiative", after=15),
    ]


def _build_rejected_calls() -> list[RejectedCall]:
    return [
        RejectedCall(
            tool_name=REJECTED_TOOL_NAME,
            arguments={"spell": "fireball"},
            result={"error": "insufficient_mana"},
        ),
    ]


def _build_turn_payload(sequence: int) -> TurnPayload:
    return TurnPayload(
        turn_id=uuid4(),
        turn_number=sequence,
        participant_id=uuid4(),
        action_mode="do",
        action_text=ACTION_TEXT,
        narration_text=_generate_narration(),
        accepted_delta=AcceptedDelta(items=_build_accepted_deltas()),
        rejected_calls=_build_rejected_calls(),
    )


async def _apply_migrations(test_url: str) -> None:
    await apply_migrations(test_url)


async def _create_connection(test_url: str) -> AsyncConnection:
    return await AsyncConnection.connect(test_url)


async def _create_template(connection: AsyncConnection) -> UUID:
    from app.models.templates import TemplateCreate
    from app.repositories import template_repo

    scenario_id = uuid4()
    await template_repo.create_template(
        connection,
        TemplateCreate(
            scenario_id=scenario_id,
            publish_revision=1,
            mode="master",
            direct_status="ready",
            enrichment_status="not_needed",
            content_hash="hash",
        ),
    )
    return scenario_id


async def _register_playthrough(
    service: IngestService, connection: AsyncConnection, playthrough_id: UUID
) -> None:
    from app.models.ingest import (
        IngestRequest,
        RegisterItem,
        RegisterPayload,
    )

    scenario_id = await _create_template(connection)
    register_item = RegisterItem(
        item_kind="register_playthrough",
        sequence=0,
        payload=RegisterPayload(
            scenario_id=scenario_id,
            publish_revision=1,
            player_entity=None,
            setup_facts=[],
        ),
    )
    request = IngestRequest(playthrough_id=playthrough_id, items=[register_item])
    await service.ingest_items(request)


async def _measure_turn_latency(
    service: IngestService,
    playthrough_id: UUID,
    sequence: int,
) -> float:
    from app.models.ingest import IngestRequest, TurnItem

    payload = _build_turn_payload(sequence)
    turn_item = TurnItem(item_kind="turn", sequence=sequence, payload=payload)
    request = IngestRequest(playthrough_id=playthrough_id, items=[turn_item])

    start = time.perf_counter()
    await service.ingest_items(request)
    elapsed_seconds = time.perf_counter() - start
    return elapsed_seconds * 1000


async def _measure_all_turns(
    service: IngestService, playthrough_id: UUID
) -> list[float]:
    latencies: list[float] = []
    for sequence in range(1, TURN_COUNT + 1):
        latency_ms = await _measure_turn_latency(service, playthrough_id, sequence)
        latencies.append(latency_ms)
    return latencies


async def main() -> None:
    settings = get_settings()
    test_db_url = settings.memory_test_database_url

    await _apply_migrations(test_db_url)
    connection = await _create_connection(test_db_url)

    try:
        service = IngestService(connection)
        playthrough_id = uuid4()

        await _register_playthrough(service, connection, playthrough_id)
        latencies = await _measure_all_turns(service, playthrough_id)

        p50 = median(latencies)
        p95 = sorted(latencies)[int(len(latencies) * 0.95)]
        max_latency = max(latencies)

        print(
            f"count={TURN_COUNT} p50={p50:.2f}ms p95={p95:.2f}ms max={max_latency:.2f}ms"
        )
    finally:
        await connection.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

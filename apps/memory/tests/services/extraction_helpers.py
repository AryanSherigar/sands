"""Builders for extraction service tests: an ingested playthrough, a respx-backed
extraction client and a service wired to a real pool and queue."""

import json
from dataclasses import dataclass
from uuid import UUID, uuid4

import httpx
import respx
from app.config import Settings
from app.integrations.extraction_queue import ExtractionQueue
from app.integrations.muse_extraction_client import MuseExtractionClient
from app.repositories import span_repo
from app.services.extraction_service import ExtractionService
from app.services.ingest_service import IngestService
from app.services.retrieval_service import RetrievalService
from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from tests.services.ingest_helpers import (
    TemplateWorld,
    TurnSpec,
    build_request,
    flush_item,
    player_payload,
    register_item,
    seed_template_world,
    turn_item,
)

TEST_API_KEY = "CANARY-EXTRACTION-KEY"
GENERATE_URL_PATTERN = r"^https://api\.meta\.ai/v1/chat/completions$"
NARRATION = "Mira swears on her blade to guard the ferry at dawn. CANARY-TURN-TEXT"
TRUNCATE_QUEUE = (
    "TRUNCATE procrastinate_jobs, procrastinate_events, "
    "procrastinate_periodic_defers, procrastinate_workers RESTART IDENTITY CASCADE"
)
EMPTY_OUTPUT: dict[str, object] = {
    "new_entities": [],
    "facts": [],
    "supersessions": [],
    "new_commitments": [],
    "commitment_updates": [],
    "scene": None,
}


@dataclass(frozen=True)
class Playthrough:
    playthrough_id: UUID
    world: TemplateWorld


def make_settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "_env_file": None,
        "extraction_api_key": TEST_API_KEY,
        "extraction_worker_count": 2,
        "extraction_stalled_seconds": 1,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


async def ingest_playthrough(
    connection: AsyncConnection,
    turns: int,
    *,
    flush: bool = False,
    narration: str = NARRATION,
) -> Playthrough:
    world = await seed_template_world(connection)
    playthrough_id = uuid4()
    items = [
        register_item(
            world.scenario_id,
            player=player_payload(world.player_authored_id, "The Wanderer"),
        )
    ]
    items += [
        turn_item(TurnSpec(sequence=n, narration=narration, action=f"I act {n}."))
        for n in range(1, turns + 1)
    ]
    if flush:
        items.append(flush_item(turns))
    await IngestService(connection).ingest_items(build_request(playthrough_id, *items))
    await connection.commit()
    return Playthrough(playthrough_id, world)


async def ingest_more_turns(
    connection: AsyncConnection, playthrough_id: UUID, first: int, last: int
) -> None:
    items = [
        turn_item(TurnSpec(sequence=n, narration=NARRATION, action=f"I act {n}."))
        for n in range(first, last + 1)
    ]
    await IngestService(connection).ingest_items(build_request(playthrough_id, *items))
    await connection.commit()


async def label_of(
    connection: AsyncConnection, playthrough_id: UUID, sequence: int
) -> str:
    spans = await span_repo.list_spans_by_sequence(
        connection, "playthrough", playthrough_id, sequence, sequence
    )
    return spans[-1].label


def extraction_ok(output: dict[str, object]) -> httpx.Response:
    body = {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"role": "assistant", "content": json.dumps(output)},
            }
        ],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20},
    }
    return httpx.Response(200, json=body)


def extraction_error(
    status_code: int, message: str = "provider-detail"
) -> httpx.Response:
    return httpx.Response(
        status_code, json={"error": {"code": status_code, "message": message}}
    )


def mock_extraction(
    router: respx.MockRouter, *responses: httpx.Response
) -> respx.Route:
    return router.post(url__regex=GENERATE_URL_PATTERN).mock(
        side_effect=list(responses) if len(responses) > 1 else None,
        return_value=responses[0] if len(responses) == 1 else None,
    )


def build_service(
    pool: AsyncConnectionPool,
    settings: Settings,
    queue: ExtractionQueue,
    *,
    is_configured: bool = True,
) -> ExtractionService:
    client = (
        MuseExtractionClient(
            api_key=TEST_API_KEY,
            base_url=settings.muse_base_url,
            model_name=settings.extraction_model_name,
            timeout_seconds=5,
            max_tokens=settings.muse_extraction_max_tokens,
            reasoning_effort=settings.muse_extraction_reasoning_effort,
        )
        if is_configured
        else None
    )
    return ExtractionService(
        pool, settings, client, queue, RetrievalService(pool, settings, None)
    )

"""Measure template direct-write latency on the test database.

Usage:
    python -m scripts.measure_template_latency     (from apps/memory/)

Reports wall time for a Hollow-Cairn-sized master template, a large master
template, and a 300k-word newbie template. Every measurement is rolled back, so
the database is left as it was found.
"""

import asyncio
import sys
import time
from uuid import uuid4

from app.config import get_settings
from app.db.migrate import apply_migrations
from app.models.templates import (
    MasterTemplateContent,
    NewbieTemplateContent,
    StoryCardPayload,
    TemplateBuildRequest,
    TemplateEntityPayload,
    TemplateFactPayload,
)
from app.services.template_service import TemplateService
from psycopg import AsyncConnection

SMALL_ENTITY_COUNT = 7
SMALL_FACT_COUNT = 7
LARGE_ENTITY_COUNT = 300
LARGE_FACT_COUNT = 900
LORE_WORD_COUNT = 300_000
WORDS_PER_PARAGRAPH = 100
CARD_COUNT = 50
LORE_WORDS = [
    "The",
    "river",
    "changed",
    "course",
    "long",
    "before",
    "the",
    "ferrymen",
    "learned",
    "to",
    "read",
    "its",
    "moods",
    "and",
    "the",
    "villages",
    "along",
    "its",
    "bank",
    "forgot",
    "the",
    "older",
    "names",
]
TARGET_SECONDS = 10.0
CONTENT_HASH = "measure"


def _master_request(entity_count: int, fact_count: int) -> TemplateBuildRequest:
    entities = [
        TemplateEntityPayload(
            entity_id=uuid4(),
            entity_type="character",
            canonical_name=f"Person {index}",
            aliases=[f"P{index}"],
            description=f"Person {index} is a long-standing resident of the valley.",
        )
        for index in range(entity_count)
    ]
    facts = [
        TemplateFactPayload(
            fact_id=uuid4(),
            subject_entity_id=entities[index % entity_count].entity_id,
            predicate="knows",
            object_entity_id=entities[(index + 1) % entity_count].entity_id,
        )
        for index in range(fact_count)
    ]
    return TemplateBuildRequest(
        scenario_id=uuid4(),
        publish_revision=1,
        mode="master",
        content_hash=CONTENT_HASH,
        master=MasterTemplateContent(entities=entities, facts=facts),
    )


def _lore_text() -> str:
    paragraph_count = LORE_WORD_COUNT // WORDS_PER_PARAGRAPH
    paragraph = " ".join(
        LORE_WORDS[index % len(LORE_WORDS)] for index in range(WORDS_PER_PARAGRAPH)
    )
    return "\n\n".join(paragraph for _ in range(paragraph_count))


def _newbie_request() -> TemplateBuildRequest:
    cards = [
        StoryCardPayload(
            card_id=f"card-{index}",
            type="Character",
            name=f"Card Person {index}",
            content=f"Card Person {index} lives beside the river.",
        )
        for index in range(CARD_COUNT)
    ]
    return TemplateBuildRequest(
        scenario_id=uuid4(),
        publish_revision=1,
        mode="newbie",
        content_hash=CONTENT_HASH,
        newbie=NewbieTemplateContent(story_cards=cards, world_lore=_lore_text()),
    )


async def _time_build(
    connection: AsyncConnection, label: str, request: TemplateBuildRequest
) -> float:
    start = time.perf_counter()
    await TemplateService(connection).build_template(request)
    elapsed = time.perf_counter() - start
    await connection.rollback()
    print(f"{label}: {elapsed:.2f}s")
    return elapsed


async def main() -> None:
    database_url = get_settings().memory_test_database_url
    await apply_migrations(database_url)
    async with await AsyncConnection.connect(database_url) as connection:
        await _time_build(
            connection,
            f"master {SMALL_ENTITY_COUNT} entities / {SMALL_FACT_COUNT} facts",
            _master_request(SMALL_ENTITY_COUNT, SMALL_FACT_COUNT),
        )
        await _time_build(
            connection,
            f"master {LARGE_ENTITY_COUNT} entities / {LARGE_FACT_COUNT} facts",
            _master_request(LARGE_ENTITY_COUNT, LARGE_FACT_COUNT),
        )
        newbie_seconds = await _time_build(
            connection,
            f"newbie {LORE_WORD_COUNT} words / {CARD_COUNT} cards",
            _newbie_request(),
        )
    verdict = "within" if newbie_seconds <= TARGET_SECONDS else "OVER"
    print(f"newbie lore is {verdict} the {TARGET_SECONDS:.0f}s target")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)

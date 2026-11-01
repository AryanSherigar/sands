"""Live preflight: does the key work, and what do cold, warm and burst calls cost in time."""

import asyncio
import json
import statistics
import time

from app.config import Settings, get_settings
from app.exceptions.extraction_exceptions import ExtractionConfigError
from app.exceptions.indexing_exceptions import EmbeddingRateLimitedError
from app.integrations.embedding_client import EmbeddingClient
from app.integrations.muse_extraction_client import MuseExtractionClient
from app.services.extraction_input import load_system_prompt, render_user_content
from pydantic import BaseModel

from eval.credentials import resolve_api_key

MILLISECONDS_PER_SECOND = 1000
PROBE_QUERY = "What did the warden promise at the cairn gate?"
WARM_CALL_COUNT = 5
PACED_CALL_COUNT = 8
PACED_INTERVAL_SECONDS = 1.0
BURST_CALL_COUNT = 10
CLIENT_TIMEOUT_SECONDS = 30
EXTRACTION_TIMEOUT_SECONDS = 60
SAMPLE_TURNS = (
    "### Turn 1 (actor: Mira)\n"
    "S1.1 [action] I tell Captain Vale I will guard the ferry at dawn.\n"
    "S1.2 [narration] Vale nods. Mira swears to guard the ferry at dawn.\n"
)


class EmbeddingPreflight(BaseModel):
    model: str
    cold_ms: float
    warm_ms: list[float]
    paced_ms: list[float]
    burst_ms: list[float]
    rate_limited_count: int
    failure: str | None = None


class ExtractionPreflight(BaseModel):
    model: str
    duration_ms: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    failure: str | None = None


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * MILLISECONDS_PER_SECOND, 1)


async def _timed_query(client: EmbeddingClient) -> float | None:
    started = time.perf_counter()
    try:
        await client.embed_query(PROBE_QUERY)
    except EmbeddingRateLimitedError:
        return None
    return _elapsed_ms(started)


async def _sequence(
    client: EmbeddingClient, count: int, gap: float
) -> list[float | None]:
    results: list[float | None] = []
    for _ in range(count):
        results.append(await _timed_query(client))
        await asyncio.sleep(gap)
    return results


def _successes(values: list[float | None]) -> list[float]:
    return [value for value in values if value is not None]


async def run_embedding_preflight(
    settings: Settings, api_key: str
) -> EmbeddingPreflight:
    client = EmbeddingClient(
        api_key,
        settings.embedding_model_name,
        settings.embedding_dim,
        CLIENT_TIMEOUT_SECONDS,
        transient_retries=0,
    )
    cold = await _timed_query(client)
    warm = await _sequence(client, WARM_CALL_COUNT, 0.0)
    paced = await _sequence(client, PACED_CALL_COUNT, PACED_INTERVAL_SECONDS)
    burst = await asyncio.gather(
        *[_timed_query(client) for _ in range(BURST_CALL_COUNT)]
    )
    every = [cold, *warm, *paced, *burst]
    return EmbeddingPreflight(
        model=settings.embedding_model_name,
        cold_ms=cold or -1.0,
        warm_ms=_successes(warm),
        paced_ms=_successes(paced),
        burst_ms=_successes(list(burst)),
        rate_limited_count=sum(1 for value in every if value is None),
    )


async def run_extraction_preflight(
    settings: Settings, api_key: str
) -> ExtractionPreflight:
    client = MuseExtractionClient(
        api_key,
        settings.muse_base_url,
        settings.extraction_model_name,
        EXTRACTION_TIMEOUT_SECONDS,
        max_tokens=settings.muse_extraction_max_tokens,
        reasoning_effort=(
            settings.extraction_thinking_level
            or settings.muse_extraction_reasoning_effort
        ),
    )
    user_content = render_user_content(
        turns=SAMPLE_TURNS,
        context="(none)",
        roster="(none)",
        tracked="(none)",
        scene="(none)",
    )
    started = time.perf_counter()
    try:
        result = await client.extract(load_system_prompt(), user_content)
    except ExtractionConfigError as error:
        return ExtractionPreflight(
            model=client.model_name, failure=type(error).__name__
        )
    return ExtractionPreflight(
        model=client.model_name,
        duration_ms=_elapsed_ms(started),
        input_tokens=result.usage.input_tokens,
        output_tokens=result.usage.output_tokens,
    )


def summarize(embedding: EmbeddingPreflight) -> dict[str, float]:
    groups = {
        "warm": embedding.warm_ms,
        "paced": embedding.paced_ms,
        "burst": embedding.burst_ms,
    }
    return {
        f"{name}_median_ms": round(statistics.median(values), 1)
        for name, values in groups.items()
        if values
    }


async def main() -> None:
    settings = get_settings()
    api_key = resolve_api_key(settings)
    embedding = await run_embedding_preflight(settings, api_key)
    extraction = await run_extraction_preflight(settings, api_key)
    print(
        json.dumps(
            {
                "embedding": embedding.model_dump(),
                "embedding_summary": summarize(embedding),
                "extraction": extraction.model_dump(),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())

"""Drives one campaign through ingest and background work on a live memory service."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from app.models.process_pending import ProcessPendingResponse

from eval.corpus_loader import Campaign
from eval.corpus_models import TurnDef
from eval.errors import HarnessError
from eval.memory_http import MemoryHttp
from eval.payloads import (
    build_flush_item,
    build_register_items,
    build_turn_items,
    playthrough_id_of,
)

INGEST_CHUNK_ITEMS = 50
MAX_SWEEP_ROUNDS = 60
RATE_LIMIT_BACKOFF_SECONDS = 5.0
BLOCKED_STEPS = {"rate_limited", "deadline_reached"}
FAILING_STEPS = {"aborted", "unconfigured"}


@dataclass
class UsageTotals:
    extraction_input_tokens: int = 0
    extraction_output_tokens: int = 0
    characters_embedded: int = 0


def _record(usage: UsageTotals, response: ProcessPendingResponse) -> None:
    usage.extraction_input_tokens += response.extraction_counts.input_tokens
    usage.extraction_output_tokens += response.extraction_counts.output_tokens
    usage.characters_embedded += response.counts.characters_embedded


def _did_work(response: ProcessPendingResponse) -> bool:
    counts, extraction = response.counts, response.extraction_counts
    return bool(
        counts.spans_embedded
        or counts.facts_embedded
        or extraction.batches_created
        or extraction.batches_applied
    )


def _is_blocked(response: ProcessPendingResponse) -> bool:
    return (
        response.embedding_step in BLOCKED_STEPS
        or response.extraction_step in BLOCKED_STEPS
    )


def _check_not_failing(response: ProcessPendingResponse) -> None:
    steps = {response.embedding_step, response.extraction_step}
    if steps & FAILING_STEPS:
        raise HarnessError(
            f"Sweep reported {sorted(steps & FAILING_STEPS)}: {response.errors}"
        )


async def drain(
    http: MemoryHttp,
    playthrough_id: UUID | None,
    usage: UsageTotals,
    on_sweep: Callable[[UsageTotals], None],
) -> None:
    """Sweep until a sweep finds nothing left to do; back off while rate limited."""
    for _ in range(MAX_SWEEP_ROUNDS):
        response = await http.process_pending(playthrough_id)
        _record(usage, response)
        on_sweep(usage)
        _check_not_failing(response)
        if _is_blocked(response):
            await asyncio.sleep(RATE_LIMIT_BACKOFF_SECONDS)
        elif not _did_work(response):
            return
    raise HarnessError("Background work did not finish within the sweep limit")


async def ingest_turns(
    http: MemoryHttp,
    campaign: Campaign,
    playthrough_key: str,
    turns: list[TurnDef],
) -> None:
    playthrough_id = playthrough_id_of(campaign, playthrough_key)
    items = build_turn_items(campaign, turns, playthrough_key)
    for start in range(0, len(items), INGEST_CHUNK_ITEMS):
        await http.ingest(playthrough_id, items[start : start + INGEST_CHUNK_ITEMS])


async def register_playthrough(
    http: MemoryHttp, campaign: Campaign, playthrough_key: str
) -> None:
    items = build_register_items(campaign, playthrough_key)
    await http.ingest(playthrough_id_of(campaign, playthrough_key), items)


async def flush_playthrough(
    http: MemoryHttp, campaign: Campaign, playthrough_key: str, last_turn: int
) -> None:
    await http.ingest(
        playthrough_id_of(campaign, playthrough_key), [build_flush_item(last_turn)]
    )

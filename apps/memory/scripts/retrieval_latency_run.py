"""Runs the timed retrieval loop and validates every response."""

import random
import time
from collections import Counter
from dataclasses import dataclass

from app.models.retrieve import RetrieveRequest, RetrieveResponse
from app.services.retrieval_service import RetrievalService
from structlog.testing import capture_logs

from scripts.retrieval_latency_queries import QueryPools, build_request
from scripts.retrieval_latency_stats import MILLISECONDS_PER_SECOND
from scripts.retrieval_latency_types import BuiltCorpus, MeasurementError

RETRIEVE_EVENT = "retrieve_completed"
FAILURE_LEVELS = {"warning", "error", "critical"}


@dataclass
class RunResult:
    latencies_ms: list[float]
    responses: list[RetrieveResponse]
    logs: list[dict[str, object]]
    kinds: Counter[str]


def build_requests(
    rng: random.Random,
    corpus: BuiltCorpus,
    pools: QueryPools,
    sequence: int,
    count: int,
) -> list[tuple[str, RetrieveRequest]]:
    return [build_request(rng, corpus, pools, sequence) for _ in range(count)]


def check_response(
    kind: str, request: RetrieveRequest, response: RetrieveResponse
) -> None:
    if response.skipped_branches:
        raise MeasurementError(
            f"Branches skipped {response.skipped_branches} for {kind} query "
            f"{request.action_text!r}."
        )


def validate_logs(
    captured: list[dict[str, object]], expected_completions: int
) -> list[dict[str, object]]:
    failures = [entry for entry in captured if entry.get("log_level") in FAILURE_LEVELS]
    if failures:
        raise MeasurementError(f"Service logged failures during the run: {failures}")
    completed = [entry for entry in captured if entry["event"] == RETRIEVE_EVENT]
    if len(completed) != expected_completions:
        raise MeasurementError(
            f"Expected {expected_completions} {RETRIEVE_EVENT} log lines, "
            f"captured {len(completed)}."
        )
    return completed


async def _timed_retrieve(
    service: RetrievalService, kind: str, request: RetrieveRequest
) -> tuple[RetrieveResponse, float]:
    started = time.perf_counter()
    response = await service.retrieve(request)
    elapsed = time.perf_counter() - started
    check_response(kind, request, response)
    return response, elapsed * MILLISECONDS_PER_SECOND


async def _retrieve_all(
    service: RetrievalService, requests: list[tuple[str, RetrieveRequest]]
) -> list[tuple[str, RetrieveResponse, float]]:
    outcomes = []
    for kind, request in requests:
        response, latency_ms = await _timed_retrieve(service, kind, request)
        outcomes.append((kind, response, latency_ms))
    return outcomes


async def run_queries(
    service: RetrievalService,
    requests: list[tuple[str, RetrieveRequest]],
    warmup_count: int,
) -> RunResult:
    with capture_logs() as captured:
        outcomes = await _retrieve_all(service, requests)
    completed = validate_logs(captured, len(requests))
    measured = outcomes[warmup_count:]
    return RunResult(
        [latency_ms for _, _, latency_ms in measured],
        [response for _, response, _ in measured],
        completed[warmup_count:],
        Counter(kind for kind, _, _ in measured),
    )

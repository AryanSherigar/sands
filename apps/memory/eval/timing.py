"""Per-stage timings read back from a run's service log; ids, counts and milliseconds only."""

import json
import statistics
from collections.abc import Iterable
from dataclasses import dataclass, field

RETRIEVE_EVENT = "retrieve_completed"
EXTRACTION_EVENT = "extraction_batch_timed"
JSON_LINE_START = "{"


@dataclass(frozen=True)
class StageTimings:
    retrieval_ms: dict[str, float] = field(default_factory=dict)
    extraction_ms: dict[str, float] = field(default_factory=dict)


def _events(lines: Iterable[str]) -> Iterable[dict[str, object]]:
    for line in lines:
        if not line.startswith(JSON_LINE_START):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            # NOTE: uvicorn writes plain text lines next to the JSON log events.
            continue
        if isinstance(event, dict):
            yield event


def _collect(samples: dict[str, list[float]], stage_ms: object) -> None:
    if not isinstance(stage_ms, dict):
        return
    for stage, millis in stage_ms.items():
        if isinstance(millis, int | float):
            samples.setdefault(str(stage), []).append(float(millis))


def _means(samples: dict[str, list[float]]) -> dict[str, float]:
    return {
        stage: statistics.fmean(values) for stage, values in sorted(samples.items())
    }


def parse_stage_timings(lines: Iterable[str]) -> StageTimings:
    retrieval: dict[str, list[float]] = {}
    extraction: dict[str, list[float]] = {}
    samples_by_event = {RETRIEVE_EVENT: retrieval, EXTRACTION_EVENT: extraction}
    for event in _events(lines):
        samples = samples_by_event.get(str(event.get("event")))
        if samples is not None:
            _collect(samples, event.get("stage_ms"))
    return StageTimings(_means(retrieval), _means(extraction))

"""Pure-Python bootstrap intervals; no dependency, deterministic for a seed."""

import random
import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from eval.scoring.retrieval import ProbeScore

BOOTSTRAP_ITERATIONS = 2000
BOOTSTRAP_SEED = 20261026
CONFIDENCE_TAIL = 0.025
MIN_SAMPLES_FOR_INTERVAL = 2


@dataclass(frozen=True)
class Interval:
    mean: float
    low: float
    high: float
    count: int


def bootstrap_interval(
    values: Sequence[float],
    iterations: int = BOOTSTRAP_ITERATIONS,
    seed: int = BOOTSTRAP_SEED,
) -> Interval | None:
    """None when there are too few samples for an interval to mean anything."""
    if len(values) < MIN_SAMPLES_FOR_INTERVAL:
        return None
    rng = random.Random(seed)
    means = sorted(
        statistics.fmean(rng.choices(values, k=len(values))) for _ in range(iterations)
    )
    low = means[int(CONFIDENCE_TAIL * iterations)]
    high = means[int((1 - CONFIDENCE_TAIL) * iterations) - 1]
    return Interval(statistics.fmean(values), low, high, len(values))


def summarize_by_class(
    scores: list[ProbeScore], metric: Callable[[ProbeScore], float]
) -> dict[str, Interval | None]:
    grouped: dict[str, list[float]] = {}
    for score in scores:
        grouped.setdefault(score.failure_class, []).append(metric(score))
    return {
        name: bootstrap_interval(values) for name, values in sorted(grouped.items())
    }

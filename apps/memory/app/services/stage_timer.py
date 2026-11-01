"""Wall-clock milliseconds per named stage of one request or batch."""

import time
from collections.abc import Iterator
from contextlib import contextmanager

MILLISECONDS_PER_SECOND = 1000


class StageTimer:
    def __init__(self) -> None:
        self.stage_ms: dict[str, int] = {}

    @contextmanager
    def measure(self, stage: str) -> Iterator[None]:
        started = time.perf_counter()
        try:
            yield
        finally:
            elapsed_seconds = time.perf_counter() - started
            self.stage_ms[stage] = round(elapsed_seconds * MILLISECONDS_PER_SECOND)

"""Sliding-window-counter estimate (Cloudflare-style) over two fixed windows."""

import math
from dataclasses import dataclass

MIN_RETRY_AFTER_SECONDS = 1


@dataclass(frozen=True)
class SlidingWindowDecision:
    is_allowed: bool
    remaining: int
    retry_after_seconds: int
    reset_seconds: int


def estimate_count(
    previous_count: int, current_count: int, elapsed_seconds: float, window_seconds: int
) -> float:
    previous_weight = max(0.0, 1.0 - elapsed_seconds / window_seconds)
    return previous_count * previous_weight + current_count


def seconds_until_allowed(
    previous_count: int,
    current_count: int,
    elapsed_seconds: float,
    window_seconds: int,
    limit: int,
) -> float:
    """Seconds until one more request would fit under the limit.

    Solves the estimate formula for the moment the previous window's decaying
    share frees a slot; if the current window alone is already full, the wait
    runs past the window boundary until the current count decays in turn.
    """
    target = limit - 1
    if current_count <= target and previous_count > 0:
        needed_weight = (target - current_count) / previous_count
        return max(0.0, window_seconds * (1.0 - needed_weight) - elapsed_seconds)
    remaining_in_window = window_seconds - elapsed_seconds
    if current_count == 0:
        return remaining_in_window
    next_window_wait = window_seconds * max(0.0, 1.0 - target / current_count)
    return remaining_in_window + next_window_wait


def decide(
    previous_count: int,
    current_count: int,
    elapsed_seconds: float,
    window_seconds: int,
    limit: int,
) -> SlidingWindowDecision:
    estimate = estimate_count(
        previous_count, current_count, elapsed_seconds, window_seconds
    )
    is_allowed = estimate <= limit
    wait = seconds_until_allowed(
        previous_count, current_count, elapsed_seconds, window_seconds, limit
    )
    return SlidingWindowDecision(
        is_allowed=is_allowed,
        remaining=max(0, math.floor(limit - estimate)),
        retry_after_seconds=0
        if is_allowed
        else max(MIN_RETRY_AFTER_SECONDS, math.ceil(wait)),
        reset_seconds=max(
            MIN_RETRY_AFTER_SECONDS, math.ceil(window_seconds - elapsed_seconds)
        ),
    )

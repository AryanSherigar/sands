"""Unit tests for the sliding-window-counter estimate and retry math."""

import pytest
from app.services.rate_limit.sliding_window import (
    decide,
    estimate_count,
    seconds_until_allowed,
)

WINDOW = 60


def test_estimate_weights_previous_window_by_remaining_overlap() -> None:
    assert estimate_count(10, 4, 15, WINDOW) == pytest.approx(10 * 0.75 + 4)


def test_estimate_ignores_previous_window_once_fully_elapsed() -> None:
    assert estimate_count(10, 4, WINDOW, WINDOW) == 4


def test_request_at_limit_is_allowed_and_next_is_rejected() -> None:
    assert decide(0, 5, 10, WINDOW, 5).is_allowed
    assert not decide(0, 6, 10, WINDOW, 5).is_allowed


def test_previous_window_burst_blocks_window_edge_doubling() -> None:
    decision = decide(5, 1, 1, WINDOW, 5)

    assert not decision.is_allowed
    assert decision.retry_after_seconds >= 1


def test_rejected_decision_reports_zero_remaining() -> None:
    assert decide(0, 9, 30, WINDOW, 5).remaining == 0


def test_allowed_decision_reports_remaining_and_no_retry() -> None:
    decision = decide(0, 2, 30, WINDOW, 5)

    assert decision.remaining == 3
    assert decision.retry_after_seconds == 0
    assert decision.reset_seconds == 30


def test_wait_for_previous_window_decay_frees_a_slot() -> None:
    wait = seconds_until_allowed(10, 0, 0, WINDOW, 5)

    assert estimate_count(10, 0, wait, WINDOW) <= 4 + 1e-9


def test_wait_runs_past_boundary_when_current_window_is_full() -> None:
    wait = seconds_until_allowed(0, 10, 20, WINDOW, 5)

    assert wait == pytest.approx(40 + WINDOW * (1 - 4 / 10))

import pytest
from app.models.world_clock import (
    MONTHS_PER_TURN,
    TURNS_PER_YEAR,
    RngState,
    TurnClock,
)
from pydantic import ValidationError


def test_turn_length_fills_the_year() -> None:
    assert MONTHS_PER_TURN * TURNS_PER_YEAR == 12


def test_clock_and_rng_round_trip() -> None:
    clock = TurnClock(turn=4, start_year=1000, start_month=3)
    rng = RngState(seed=7)
    assert TurnClock.model_validate_json(clock.model_dump_json()) == clock
    assert RngState.model_validate_json(rng.model_dump_json()) == rng


def test_month_out_of_range_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TurnClock(turn=0, start_year=1000, start_month=13)


def test_extra_key_is_rejected() -> None:
    with pytest.raises(ValidationError):
        RngState.model_validate({"seed": 1, "x": 1})

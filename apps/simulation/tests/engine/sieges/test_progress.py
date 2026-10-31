from app.engine.sieges.progress import progress_per_turn
from strategy_contracts.siege import SiegeTuning

TUNING = SiegeTuning()


def test_progress_scales_with_troops_and_garrison() -> None:
    assert progress_per_turn(600, 100, TUNING) == 30
    assert progress_per_turn(200, 100, TUNING) == 10


def test_bigger_garrison_slows_the_siege() -> None:
    assert progress_per_turn(600, 300, TUNING) < progress_per_turn(600, 100, TUNING)


def test_progress_never_below_min_step() -> None:
    assert progress_per_turn(1, 100, TUNING) == 5


def test_progress_capped_at_full() -> None:
    assert progress_per_turn(100000, 0, TUNING) == 100

from app.engine.pressure.bands import to_band
from strategy_contracts.pressure import PressureBand, PressureTuning

TUNING = PressureTuning()


def test_each_threshold_value_belongs_to_the_higher_band() -> None:
    assert to_band(0, TUNING) is PressureBand.VERY_LOW
    assert to_band(19, TUNING) is PressureBand.VERY_LOW
    assert to_band(20, TUNING) is PressureBand.LOW
    assert to_band(40, TUNING) is PressureBand.MEDIUM
    assert to_band(60, TUNING) is PressureBand.HIGH
    assert to_band(80, TUNING) is PressureBand.VERY_HIGH
    assert to_band(100, TUNING) is PressureBand.VERY_HIGH

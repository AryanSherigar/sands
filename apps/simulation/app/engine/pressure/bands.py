from bisect import bisect_right

from strategy_contracts.pressure import PressureBand, PressureTuning

ORDERED_BANDS = tuple(PressureBand)


def to_band(value: int, tuning: PressureTuning) -> PressureBand:
    return ORDERED_BANDS[bisect_right(tuning.band_thresholds, value)]

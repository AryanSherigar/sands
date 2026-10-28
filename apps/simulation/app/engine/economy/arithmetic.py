PERCENT = 100


def ceil_division(numerator: int, denominator: int) -> int:
    return -(-numerator // denominator)


def percent_of(value: int, percent: int) -> int:
    return value * percent // PERCENT


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))

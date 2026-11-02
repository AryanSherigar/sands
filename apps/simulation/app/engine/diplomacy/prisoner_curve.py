def prisoner_curve(troops: int, ceiling: int, half_troops: int) -> int:
    """Hill curve: a handful of captives score nothing, thousands matter, and ten times the troops is only about twice the score."""
    squared = troops * troops
    return ceiling * squared // (squared + half_troops * half_troops)

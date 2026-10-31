from app.engine.economy.arithmetic import clamp
from strategy_contracts.siege import SiegeTuning


def progress_per_turn(troops: int, garrison: int, tuning: SiegeTuning) -> int:
    raw = troops * tuning.troop_factor // (garrison + tuning.garrison_floor)
    return clamp(raw, tuning.min_step, tuning.full_progress)

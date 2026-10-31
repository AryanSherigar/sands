from app.models.world_character import LeaderState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.succession import HealthBand

BAND_ORDER = (HealthBand.ROBUST, HealthBand.AILING, HealthBand.FAILING)


def _band_for_age(age: int, scenario: StrategyScenario) -> HealthBand:
    tuning = scenario.tuning.succession
    if age >= tuning.failing_age:
        return HealthBand.FAILING
    if age >= tuning.ailing_age:
        return HealthBand.AILING
    return HealthBand.ROBUST


def health_band(leader: LeaderState, scenario: StrategyScenario) -> HealthBand:
    band = _band_for_age(leader.age, scenario)
    if leader.stress < scenario.tuning.succession.stress_worsens_at:
        return band
    worse_index = min(BAND_ORDER.index(band) + 1, len(BAND_ORDER) - 1)
    return BAND_ORDER[worse_index]


def death_per_mille(leader: LeaderState, scenario: StrategyScenario) -> int:
    tuning = scenario.tuning.succession
    base = tuning.death_per_mille[health_band(leader, scenario)]
    years_past = max(0, leader.age - tuning.failing_age)
    chance = base + tuning.old_age_step_per_mille * years_past
    return max(0, min(tuning.max_death_per_mille, chance))

from app.engine.succession.health import death_per_mille, health_band
from app.models.world_character import LeaderState
from strategy_contracts.succession import HealthBand

from tests.engine.succession.builders import (
    PLAYER,
    SCENARIO,
    leader_of,
    make_succession_world,
)


def _leader(age: int, stress: int = 0) -> LeaderState:
    leader = leader_of(make_succession_world(), PLAYER)
    leader.age = age
    leader.stress = stress
    return leader


def test_band_edges_55_and_70() -> None:
    assert health_band(_leader(54), SCENARIO) is HealthBand.ROBUST
    assert health_band(_leader(55), SCENARIO) is HealthBand.AILING
    assert health_band(_leader(69), SCENARIO) is HealthBand.AILING
    assert health_band(_leader(70), SCENARIO) is HealthBand.FAILING


def test_high_stress_worsens_one_band_not_past_failing() -> None:
    assert health_band(_leader(30, stress=70), SCENARIO) is HealthBand.AILING
    assert health_band(_leader(60, stress=70), SCENARIO) is HealthBand.FAILING
    assert health_band(_leader(90, stress=100), SCENARIO) is HealthBand.FAILING
    assert health_band(_leader(30, stress=69), SCENARIO) is HealthBand.ROBUST


def test_death_chance_follows_the_table_below_failing_age() -> None:
    assert death_per_mille(_leader(30), SCENARIO) == 2
    assert death_per_mille(_leader(60), SCENARIO) == 25
    assert death_per_mille(_leader(70), SCENARIO) == 120


def test_each_year_past_failing_age_adds_the_step() -> None:
    assert death_per_mille(_leader(75), SCENARIO) == 120 + 5 * 5


def test_death_chance_clamped_for_age_200_and_stress_100() -> None:
    assert death_per_mille(_leader(200, stress=100), SCENARIO) == 500

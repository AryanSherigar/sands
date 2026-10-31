from app.engine.rng import derive_rng
from app.engine.succession.roll import roll_ruler_deaths
from app.models.world_state import WorldState
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.succession import HealthBand

from tests.engine.succession.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    leader_of,
    make_succession_world,
    tuned,
)

CERTAIN_DEATH = {band: 1000 for band in HealthBand}
NO_DEATH = {band: 0 for band in HealthBand}


def _rng(world: WorldState):
    return derive_rng(world.rng.seed, world.clock.turn, "time")


def _roll(world: WorldState, scenario: StrategyScenario) -> list[tuple[str, str]]:
    return roll_ruler_deaths(world, scenario, _rng(world))


def _deadly() -> StrategyScenario:
    return tuned(SCENARIO, death_per_mille=CERTAIN_DEATH, max_death_per_mille=1000)


def test_same_seed_same_deaths() -> None:
    first = make_succession_world()
    second = make_succession_world()
    scenario = tuned(
        SCENARIO, death_per_mille={**CERTAIN_DEATH, HealthBand.ROBUST: 500}
    )

    assert _roll(first, scenario) == _roll(second, scenario)


def test_zero_chance_never_kills() -> None:
    world = make_succession_world()
    scenario = tuned(SCENARIO, death_per_mille=NO_DEATH, old_age_step_per_mille=0)

    assert _roll(world, scenario) == []


def test_full_chance_always_kills_every_living_ruler() -> None:
    world = make_succession_world()

    deaths = _roll(world, _deadly())

    killed = {faction_id for faction_id, _ in deaths}
    assert {CAUTIOUS_RIVAL, WRATHFUL_RIVAL} <= killed


def test_cause_is_old_age_past_failing_age_otherwise_illness() -> None:
    world = make_succession_world()
    leader_of(world, WRATHFUL_RIVAL).age = 80
    leader_of(world, CAUTIOUS_RIVAL).age = 30

    causes = dict(_roll(world, _deadly()))

    assert causes[WRATHFUL_RIVAL] == "old_age"
    assert causes[CAUTIOUS_RIVAL] == "illness"


def test_destroyed_and_leaderless_factions_skipped() -> None:
    world = make_succession_world()
    world.factions[CAUTIOUS_RIVAL].is_destroyed = True
    world.factions[WRATHFUL_RIVAL].leader_id = None

    killed = {faction_id for faction_id, _ in _roll(world, _deadly())}

    assert CAUTIOUS_RIVAL not in killed
    assert WRATHFUL_RIVAL not in killed
    assert killed == set()


def test_dead_leaders_are_not_rolled_again() -> None:
    world = make_succession_world()
    leader_of(world, CAUTIOUS_RIVAL).is_alive = False

    killed = {faction_id for faction_id, _ in _roll(world, _deadly())}

    assert CAUTIOUS_RIVAL not in killed


def test_legacy_worlds_never_roll() -> None:
    world = make_succession_world()
    world.succession_ruleset = 0

    assert _roll(world, _deadly()) == []


def test_roll_independent_of_faction_iteration_order() -> None:
    world = make_succession_world()
    reversed_world = world.model_copy(deep=True)
    reversed_world.factions = dict(reversed(list(world.factions.items())))
    scenario = tuned(
        SCENARIO, death_per_mille={**CERTAIN_DEATH, HealthBand.ROBUST: 500}
    )

    assert _roll(world, scenario) == _roll(reversed_world, scenario)


def test_the_players_ruler_never_rolls_to_die() -> None:
    world = make_succession_world()
    leader_of(world, PLAYER).age = 99
    leader_of(world, PLAYER).stress = 100

    killed = {faction_id for faction_id, _ in _roll(world, _deadly())}

    assert PLAYER not in killed

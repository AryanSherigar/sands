from app.engine.internal.phase import InternalPhase
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.models.world_diplomacy import WarState
from app.models.world_events import PhaseName
from strategy_contracts.scenario import InternalTuning, StrategyScenario, Tuning
from tests.engine.economy.builders import (
    HOME,
    PLAYER,
    make_faction,
    make_region,
    make_world,
)


def _context(scenario: StrategyScenario) -> PhaseContext:
    return PhaseContext(
        scenario=scenario,
        orders=(),
        rng=derive_rng(11, 0, PhaseName.INTERNAL.value),
        resolved_outcomes={},
        recorded_answers={},
    )


def _scenario(**overrides: object) -> StrategyScenario:
    return StrategyScenario(tuning=Tuning(internal=InternalTuning(**overrides)))


def test_internal_phase_applies_war_pressure_and_opens_one_uprising() -> None:
    world = make_world(
        regions=[make_region(HOME, PLAYER, unrest=80)],
        factions=[make_faction(PLAYER)],
    )
    world.internal_ruleset = 1
    world.factions[PLAYER].stability = 40
    world.wars = [
        WarState(
            id="war_1",
            attacker_id=PLAYER,
            defender_id="house_b",
            started_turn=0,
        )
    ]
    world.battle_losses[PLAYER] = 200

    result = InternalPhase().run(
        world, _context(_scenario(revolt_base_chance_percent=100))
    )

    faction = result.world.factions[PLAYER]
    assert faction.war_exhaustion == 4
    assert faction.stability == 36
    assert result.world.regions[HOME].unrest == 81
    assert result.world.battle_losses == {}
    assert [uprising.region_id for uprising in result.world.uprisings] == [HOME]
    assert [event.kind for event in result.events] == [
        "faction_war_pressure_changed",
        "regional_unrest_changed",
        "uprising_started",
    ]


def test_internal_phase_never_applies_new_rules_to_a_legacy_world() -> None:
    world = make_world(
        regions=[make_region(HOME, PLAYER, unrest=100)],
        factions=[make_faction(PLAYER)],
    )
    world.factions[PLAYER].stability = 20
    before = world.model_dump(mode="json")

    result = InternalPhase().run(
        world, _context(_scenario(revolt_base_chance_percent=100))
    )

    assert result.world.model_dump(mode="json") == before
    assert result.events == []

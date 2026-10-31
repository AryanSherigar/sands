import pytest
from app.engine.commands.application import accept_command
from app.engine.internal.phase import InternalPhase
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import ResolveUprisingCommand
from app.models.world_events import PhaseName
from app.models.world_internal import (
    UprisingArchetype,
    UprisingResponse,
    UprisingStage,
    UprisingState,
)
from strategy_contracts.enums import TaxRate
from strategy_contracts.scenario import InternalTuning, StrategyScenario, Tuning
from tests.engine.economy.builders import (
    HOME,
    PLAYER,
    make_faction,
    make_region,
    make_world,
)

OTHER = "region_other"


def _scenario(**overrides: object) -> StrategyScenario:
    return StrategyScenario(tuning=Tuning(internal=InternalTuning(**overrides)))


def _context(scenario: StrategyScenario) -> PhaseContext:
    return PhaseContext(
        scenario=scenario,
        orders=(),
        rng=derive_rng(11, 0, PhaseName.INTERNAL.value),
        resolved_outcomes={},
        recorded_answers={},
    )


def _uprising(
    archetype: UprisingArchetype, stage: UprisingStage, **overrides: int
) -> UprisingState:
    return UprisingState(
        id="uprising_home_0",
        region_id=HOME,
        faction_id=PLAYER,
        started_turn=0,
        trigger_unrest=80,
        income_penalty_percent=50,
        manpower_penalty_percent=50,
        supply_penalty_percent=50,
        archetype=archetype,
        stage=stage,
        **overrides,
    )


def _world(uprising: UprisingState | None = None, tax_rate: TaxRate = TaxRate.NORMAL):
    world = make_world(
        regions=[
            make_region(HOME, PLAYER, unrest=80),
            make_region(OTHER, PLAYER, unrest=50),
        ],
        factions=[make_faction(PLAYER, tax_rate=tax_rate)],
    )
    world.internal_ruleset = 2
    world.clock.turn = 5
    if uprising is not None:
        world.uprisings = [uprising]
    return world


def _run(world, **overrides: object):
    scenario = _scenario(**{"revolt_base_chance_percent": 0, **overrides})
    return InternalPhase().run(world, _context(scenario))


def test_high_taxes_open_a_petition_and_a_stressed_realm_opens_a_rebellion() -> None:
    petition_world = _world(tax_rate=TaxRate.HIGH)
    petition = _run(petition_world, revolt_base_chance_percent=100).world.uprisings
    rebellion_world = _world()
    rebellion_world.factions[PLAYER].war_exhaustion = 90
    rebellion = _run(rebellion_world, revolt_base_chance_percent=100).world.uprisings

    assert petition[0].archetype is UprisingArchetype.PETITION
    assert petition[0].stage is UprisingStage.UNREST
    assert rebellion[0].archetype is UprisingArchetype.REBELLION
    assert rebellion[0].stage is UprisingStage.ARMED
    assert rebellion[0].income_penalty_percent == 90


def test_neglected_petition_escalates_and_deepens_penalties() -> None:
    world = _world(_uprising(UprisingArchetype.PETITION, UprisingStage.UNREST))

    result = _run(world, uprising_escalate_after_turns=1)

    uprising = result.world.uprisings[0]
    assert uprising.stage is UprisingStage.RIOT
    assert uprising.income_penalty_percent == 70
    assert "uprising_stage_changed" in [event.kind for event in result.events]


def test_garrison_eases_a_riot_back_a_stage_and_cools_the_region() -> None:
    world = _world(_uprising(UprisingArchetype.RIOT, UprisingStage.RIOT))
    world.regions[HOME].garrison = 10

    result = _run(world, uprising_ease_after_turns=1)

    assert result.world.uprisings[0].stage is UprisingStage.UNREST
    assert result.world.uprisings[0].income_penalty_percent == 30
    assert result.world.regions[HOME].unrest == 76


def test_armed_uprising_left_alone_flips_the_region_to_independent() -> None:
    uprising = _uprising(
        UprisingArchetype.REBELLION, UprisingStage.ARMED, turns_in_stage=3
    )
    world = _world(uprising)

    result = _run(world, uprising_armed_flip_turns=4)

    assert result.world.regions[HOME].owner_id is None
    assert result.world.uprisings == []
    assert "uprising_flipped" in [event.kind for event in result.events]


def test_lifecycle_is_deterministic() -> None:
    first = _run(_world(_uprising(UprisingArchetype.PETITION, UprisingStage.UNREST)))
    second = _run(_world(_uprising(UprisingArchetype.PETITION, UprisingStage.UNREST)))

    assert first.world.model_dump(mode="json") == second.world.model_dump(mode="json")


def _queue(world, response: UprisingResponse):
    return accept_command(
        world,
        StrategyScenario(),
        ResolveUprisingCommand(
            faction_id=PLAYER, uprising_id="uprising_home_0", response=response
        ),
        command_id="resolve",
        operation_id="resolve",
        actor_id="owner",
        faction_id=PLAYER,
        expected_turn=5,
        expected_wave=0,
    )


def _respond(world, response: UprisingResponse):
    queued = _queue(world, response).world
    return _run(queued).world


def test_concessions_cost_reputation_and_stir_other_restless_regions() -> None:
    world = _world(_uprising(UprisingArchetype.PETITION, UprisingStage.UNREST))
    before = world.factions[PLAYER].reputation

    result = _respond(world, UprisingResponse.CONCESSIONS)

    assert result.factions[PLAYER].reputation == before - 5
    assert result.regions[OTHER].unrest == 55


def test_conceding_to_a_rebellion_costs_more_reputation() -> None:
    world = _world(_uprising(UprisingArchetype.REBELLION, UprisingStage.ARMED))
    before = world.factions[PLAYER].reputation

    result = _respond(world, UprisingResponse.CONCESSIONS)

    assert result.factions[PLAYER].reputation == before - 10


def test_restore_order_leaves_a_grudge_that_keeps_unrest_rising() -> None:
    world = _world(_uprising(UprisingArchetype.PETITION, UprisingStage.UNREST))

    result = _respond(world, UprisingResponse.RESTORE_ORDER)

    assert result.region_grudges == {HOME: 10}


def test_a_leaderless_riot_cannot_be_granted_demands() -> None:
    world = _world(_uprising(UprisingArchetype.RIOT, UprisingStage.RIOT))

    with pytest.raises(CommandError) as error:
        _respond(world, UprisingResponse.CONCESSIONS)

    assert error.value.code == "no_spokesperson"


def test_a_queued_answer_waits_for_end_turn_and_costs_an_order() -> None:
    world = _world(_uprising(UprisingArchetype.PETITION, UprisingStage.UNREST))
    before = world.factions[PLAYER].orders_remaining

    queued = _queue(world, UprisingResponse.CONCESSIONS)

    assert queued.world.uprisings != []
    assert queued.world.factions[PLAYER].orders_remaining == before - 1
    assert queued.command is not None and queued.command.status.value == "accepted"


def test_an_answer_queued_in_time_lands_before_the_uprising_escalates() -> None:
    uprising = _uprising(
        UprisingArchetype.PETITION, UprisingStage.UNREST, turns_in_stage=2
    )
    queued = _queue(_world(uprising), UprisingResponse.CONCESSIONS).world

    result = _run(queued, uprising_escalate_after_turns=3)

    assert result.world.uprisings == []
    assert "uprising_stage_changed" not in [event.kind for event in result.events]
    assert next(event.kind for event in result.events) == "uprising_resolved"

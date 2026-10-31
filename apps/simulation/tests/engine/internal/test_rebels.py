from app.engine.economy.state import active_faction_ids
from app.engine.endings import is_conquest
from app.engine.internal.phase import InternalPhase
from app.engine.internal.rebels import rebel_army_id
from app.engine.movement.contact import ContactKind, classify_entry
from app.engine.phases import PhaseContext
from app.engine.rng import derive_rng
from app.models.world_army import ArmyState
from app.models.world_events import PhaseName
from app.models.world_internal import (
    REBEL_FACTION_ID,
    UprisingArchetype,
    UprisingStage,
    UprisingState,
)
from app.services.world_projection import project_rivals
from strategy_contracts.enums import RelationStatus, TroopType
from strategy_contracts.scenario import InternalTuning, StrategyScenario, Tuning
from tests.engine.economy.builders import (
    HOME,
    PLAYER,
    make_faction,
    make_region,
    make_world,
)

RIVAL = "house_rival"


def _context(scenario: StrategyScenario) -> PhaseContext:
    return PhaseContext(
        scenario=scenario,
        orders=(),
        rng=derive_rng(11, 0, PhaseName.INTERNAL.value),
        resolved_outcomes={},
        recorded_answers={},
    )


def _run(world, **overrides: object):
    internal = InternalTuning(**{"revolt_base_chance_percent": 0, **overrides})
    scenario = StrategyScenario(tuning=Tuning(internal=internal))
    return InternalPhase().run(world, _context(scenario))


def _world(stage: UprisingStage = UprisingStage.ARMED, **uprising: object):
    world = make_world(
        regions=[make_region(HOME, PLAYER, population=1000, unrest=80)],
        factions=[make_faction(PLAYER, is_player=True), make_faction(RIVAL)],
    )
    world.internal_ruleset = 2
    world.clock.turn = 5
    world.uprisings = [
        UprisingState(
            id="uprising_home_0",
            region_id=HOME,
            faction_id=PLAYER,
            started_turn=0,
            trigger_unrest=80,
            income_penalty_percent=50,
            manpower_penalty_percent=50,
            supply_penalty_percent=50,
            archetype=UprisingArchetype.REBELLION,
            stage=stage,
            **uprising,
        )
    ]
    return world


def test_an_armed_uprising_raises_a_rebel_army_at_war_with_everyone() -> None:
    result = _run(_world())

    army = result.world.armies[rebel_army_id("uprising_home_0")]
    assert army.owner_id == REBEL_FACTION_ID
    assert army.location_id == HOME
    assert army.troops == {TroopType.INFANTRY: 50}
    assert result.world.uprisings[0].has_rebel_army is True
    assert {
        relation.status
        for relation in result.world.relations
        if REBEL_FACTION_ID in (relation.faction_a, relation.faction_b)
    } == {RelationStatus.WAR}
    assert "rebel_army_raised" in [event.kind for event in result.events]


def test_a_garrisoned_region_raises_no_rebel_army() -> None:
    world = _world()
    world.regions[HOME].garrison = 5

    result = _run(world)

    assert result.world.armies == {}
    assert REBEL_FACTION_ID not in result.world.factions


def test_a_riot_below_the_armed_stage_raises_no_army() -> None:
    result = _run(_world(UprisingStage.RIOT))

    assert result.world.armies == {}


def test_destroying_the_rebel_army_ends_the_uprising_and_calms_the_region() -> None:
    raised = _run(_world()).world
    del raised.armies[rebel_army_id("uprising_home_0")]
    raised.clock.turn = 6

    result = _run(raised)

    assert result.world.uprisings == []
    assert result.world.regions[HOME].unrest == 40
    assert result.world.uprising_cooldowns[HOME] == 6
    assert "uprising_crushed" in [event.kind for event in result.events]


def test_the_rebel_faction_is_left_out_of_economy_rivals_and_conquest() -> None:
    world = _run(_world()).world

    assert REBEL_FACTION_ID not in active_faction_ids(world)
    rivals = project_rivals(world, StrategyScenario(), PLAYER)
    assert REBEL_FACTION_ID not in [item.faction_id for item in rivals]
    world.factions[RIVAL].capital_region_id = HOME
    world.regions[HOME].owner_id = PLAYER
    assert is_conquest(world) is True


def test_a_player_army_meets_the_rebels_in_battle() -> None:
    world = _run(_world()).world
    world.armies["player_army"] = ArmyState(
        id="player_army",
        owner_id=PLAYER,
        troops={TroopType.INFANTRY: 100},
        morale=80,
        location_id="elsewhere",
    )

    contact = classify_entry(world, world.armies["player_army"], HOME)

    assert contact.kind is ContactKind.BATTLE


def test_answering_an_armed_uprising_disperses_its_rebel_army() -> None:
    from app.engine.commands.application import accept_command
    from app.models.battle_command import ResolveUprisingCommand
    from app.models.world_internal import UprisingResponse

    raised = _run(_world()).world
    queued = accept_command(
        raised,
        StrategyScenario(),
        ResolveUprisingCommand(
            faction_id=PLAYER,
            uprising_id="uprising_home_0",
            response=UprisingResponse.CONCESSIONS,
        ),
        command_id="resolve",
        operation_id="resolve",
        actor_id="owner",
        faction_id=PLAYER,
        expected_turn=5,
        expected_wave=0,
    ).world

    result = _run(queued)

    assert result.world.uprisings == []
    assert rebel_army_id("uprising_home_0") not in result.world.armies


def test_a_lost_region_takes_its_rebel_army_with_it() -> None:
    world = _run(_world()).world
    world.uprisings[0].turns_in_stage = 3

    result = _run(world, uprising_armed_flip_turns=4)

    assert result.world.regions[HOME].owner_id is None
    assert rebel_army_id("uprising_home_0") not in result.world.armies

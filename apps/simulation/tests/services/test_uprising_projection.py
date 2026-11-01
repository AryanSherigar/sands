from app.models.world_internal import (
    UprisingArchetype,
    UprisingResponse,
    UprisingStage,
    UprisingState,
)
from app.services.uprising_projection import project_uprisings
from strategy_contracts.events import EffectKind
from strategy_contracts.scenario import StrategyScenario
from tests.engine.economy.builders import (
    HOME,
    PLAYER,
    make_faction,
    make_region,
    make_world,
)


def _world(archetype: UprisingArchetype, stage: UprisingStage):
    world = make_world(
        regions=[make_region(HOME, PLAYER, unrest=80)],
        factions=[make_faction(PLAYER)],
    )
    world.internal_ruleset = 2
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
            archetype=archetype,
            stage=stage,
            turns_in_stage=1,
        )
    ]
    return world


def test_a_petition_offers_every_response_with_signed_previews() -> None:
    world = _world(UprisingArchetype.PETITION, UprisingStage.UNREST)

    view = project_uprisings(world, StrategyScenario(), PLAYER)[0]

    assert [item.id for item in view.responses] == [
        UprisingResponse.CONCESSIONS,
        UprisingResponse.NEGOTIATE,
        UprisingResponse.RESTORE_ORDER,
    ]
    concessions = view.responses[0]
    assert concessions.order_cost == 1
    assert (EffectKind.REPUTATION, -5) in [
        (item.kind, item.amount) for item in concessions.effects
    ]
    assert view.turns_until_change == 2
    assert view.is_final_stage is False


def test_a_riot_offers_only_restoring_order() -> None:
    world = _world(UprisingArchetype.RIOT, UprisingStage.RIOT)

    view = project_uprisings(world, StrategyScenario(), PLAYER)[0]

    assert [item.id for item in view.responses] == [UprisingResponse.RESTORE_ORDER]


def test_an_armed_uprising_reports_the_final_stage() -> None:
    world = _world(UprisingArchetype.REBELLION, UprisingStage.ARMED)

    view = project_uprisings(world, StrategyScenario(), PLAYER)[0]

    assert view.is_final_stage is True
    assert view.turns_until_change == 3
    assert view.responses[0].effects[2].amount == -10


def test_a_rebel_army_reports_its_strength_to_the_owner() -> None:
    from app.engine.internal.rebel_armies import rebel_army_id
    from app.models.world_army import ArmyState
    from strategy_contracts.enums import TroopType

    world = _world(UprisingArchetype.REBELLION, UprisingStage.ARMED)
    world.armies[rebel_army_id("uprising_home_0")] = ArmyState(
        id=rebel_army_id("uprising_home_0"),
        owner_id="rebels",
        troops={TroopType.INFANTRY: 40},
        morale=70,
        location_id=HOME,
    )

    view = project_uprisings(world, StrategyScenario(), PLAYER)[0]

    assert view.rebel_troops == 40

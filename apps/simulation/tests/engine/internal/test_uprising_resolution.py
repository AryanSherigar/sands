from app.engine.commands.application import accept_command
from app.models.battle_command import ResolveUprisingCommand
from app.models.world_internal import UprisingResponse, UprisingState
from strategy_contracts.scenario import StrategyScenario
from tests.engine.economy.builders import (
    HOME,
    PLAYER,
    make_faction,
    make_region,
    make_world,
)


def test_resolve_uprising_applies_immediately_and_starts_cooldown() -> None:
    world = make_world(
        regions=[make_region(HOME, PLAYER, unrest=80)], factions=[make_faction(PLAYER)]
    )
    world.internal_ruleset = 1
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
        )
    ]

    result = accept_command(
        world,
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
        expected_turn=0,
        expected_wave=0,
    )

    assert result.command is not None and result.command.status.value == "applied"
    assert result.world.uprisings == []
    assert result.world.uprising_cooldowns == {HOME: 0}
    assert result.world.regions[HOME].unrest == 50
    assert result.world.factions[PLAYER].stability == 62
    assert [event.kind for event in result.events] == ["uprising_resolved"]

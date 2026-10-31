import pytest
from app.engine.hashing import world_hash
from app.engine.movement.engagement import armies_in_open_battle
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import (
    CommitReservesCommand,
    SetPlanCommand,
    SurrenderCommand,
    WithdrawCommand,
)
from app.models.world_battle import (
    BattleOutcome,
    BattleStatus,
    ContingentStatus,
    StandingPlan,
)
from app.models.world_character import CommanderState, CommanderStatus
from strategy_contracts.battle import (
    Formation,
    ReservePolicy,
    SupplyState,
    Tactic,
    Weather,
)
from strategy_contracts.enums import Terrain, TroopType

from tests.engine.battles.builders import (
    ALLY,
    ATTACKER,
    BATTLE_ID,
    DEFENDER,
    REGION,
    battle_fixture,
    command,
    exchange,
    start_battle,
)
from tests.engine.movement.builders import make_army


def test_allied_contingents_share_mountain_width_and_partition_soldiers() -> None:
    ally = make_army("army_c", ALLY, REGION, {TroopType.INFANTRY: 1000})
    world, scenario = battle_fixture(terrain=Terrain.MOUNTAIN, extra_armies=[ally])
    start_battle(world, scenario)
    attackers = [
        contingent
        for contingent in world.battles[0].contingents.values()
        if contingent.faction_id != DEFENDER
    ]
    assert (
        sum(
            sum(deployment.active.values())
            for contingent in attackers
            for deployment in contingent.deployments.values()
        )
        == 225
    )
    assert [
        sum(contingent.deployments[contingent.army_ids[0]].active.values())
        for contingent in attackers
    ] == [113, 112]
    for contingent in attackers:
        deployment = contingent.deployments[contingent.army_ids[0]]
        assert (
            deployment.active[TroopType.INFANTRY]
            + deployment.reserve[TroopType.INFANTRY]
            == 1000
        )


def test_both_sides_deal_damage_even_when_one_would_be_destroyed_first() -> None:
    world, scenario = battle_fixture(
        10,
        10,
        casualty_rate_percent=100,
        supply_attack_percent={state: 100 for state in SupplyState},
        weather_attack_percent={weather: 100 for weather in Weather},
        random_damage_min_percent=100,
        random_damage_max_percent=100,
        formation_reserve_percent={formation: 0 for formation in Formation},
    )
    start_battle(world, scenario)
    result = exchange(world, scenario)
    assert result.world.armies == {}
    assert [sum(row.combat_losses.values()) for row in result.receipt.accounting] == [
        10,
        10,
    ]
    assert result.delta.battle.outcome == BattleOutcome.MUTUAL_DISENGAGEMENT


def test_exchange_is_repeatable_and_does_not_mutate_input_or_shared_budget() -> None:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    before = world.model_dump(mode="json")
    first = exchange(world, scenario)
    second = exchange(world, scenario)
    assert first == second
    assert world.model_dump(mode="json") == before
    assert first.world.factions == world.factions
    assert first.world.counters == world.counters
    assert first.receipt.input_hash == world_hash(world)
    assert first.receipt.output_hash == world_hash(first.world)
    assert first.receipt.rule_version == scenario.tuning.battle.rule_version
    assert first.receipt.total_exchange == 1
    assert first.world.armies["army_a"].fatigue == 12
    assert all(event.seq == 0 for event in first.events)


def test_explicit_surrender_captures_survivors_and_commander_once() -> None:
    world, scenario = battle_fixture(100, 100)
    world.armies["army_a"].commander_id = "commander_a"
    world.commanders["commander_a"] = CommanderState(
        id="commander_a", name="A", faction_id=ATTACKER, army_id="army_a"
    )
    start_battle(world, scenario)
    surrender = command(SurrenderCommand(faction_id=ATTACKER, battle_id=BATTLE_ID))
    result = exchange(world, scenario, [surrender])
    assert "army_a" not in result.world.armies
    assert sum(prisoner.troop_count for prisoner in result.world.prisoners) == 100
    assert len(result.world.prisoners) == 2
    assert result.world.commanders["commander_a"].status == CommanderStatus.CAPTURED
    assert result.world.commanders["commander_a"].army_id is None
    assert result.delta.battle.outcome == BattleOutcome.ATTACKER_SURRENDER
    assert result.receipt.accounting[0].captives == {TroopType.INFANTRY: 100}
    assert result.world.armies["army_b"].troops == {TroopType.INFANTRY: 100}
    with pytest.raises(SimulationServiceError, match="resolved"):
        exchange(result.world, scenario, [surrender])


def test_simultaneous_whole_side_surrender_disengages_without_capture() -> None:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    commands = [
        command(
            SurrenderCommand(faction_id=faction, battle_id=BATTLE_ID), identity=faction
        )
        for faction in (ATTACKER, DEFENDER)
    ]
    result = exchange(world, scenario, commands)
    assert result.world.prisoners == []
    assert result.world.armies == world.armies
    assert result.delta.battle.outcome == BattleOutcome.MUTUAL_DISENGAGEMENT


def test_surrender_cannot_capture_or_command_an_allied_contingent() -> None:
    ally = make_army("army_c", ALLY, REGION)
    world, scenario = battle_fixture(extra_armies=[ally], casualty_rate_percent=0)
    start_battle(world, scenario)
    result = exchange(
        world,
        scenario,
        [command(SurrenderCommand(faction_id=ATTACKER, battle_id=BATTLE_ID))],
    )
    assert "army_c" in result.world.armies
    assert result.delta.battle.status != BattleStatus.RESOLVED
    assert result.delta.battle.contingents[ALLY].status == ContingentStatus.FIGHTING


def test_destroyed_army_releases_commander_without_capturing() -> None:
    world, scenario = battle_fixture(1, 1000)
    world.armies["army_a"].commander_id = "commander_a"
    world.commanders["commander_a"] = CommanderState(
        id="commander_a", name="A", faction_id=ATTACKER, army_id="army_a"
    )
    start_battle(world, scenario)
    result = exchange(world, scenario)
    assert "army_a" not in result.world.armies
    assert result.world.commanders["commander_a"].status == CommanderStatus.ACTIVE
    assert result.world.commanders["commander_a"].army_id is None


def test_commit_reserves_increases_shared_engagement_without_adding_soldiers() -> None:
    world, scenario = battle_fixture(terrain=Terrain.MOUNTAIN)
    start_battle(world, scenario)
    result = exchange(
        world,
        scenario,
        [command(CommitReservesCommand(faction_id=ATTACKER, battle_id=BATTLE_ID))],
    )
    row = result.receipt.accounting[1]
    assert result.delta.battle.contingents[ATTACKER].has_committed_reserves
    assert sum(row.combat_losses.values()) > 0
    assert (
        sum(
            result.delta.battle.contingents[ATTACKER]
            .deployments["army_a"]
            .active.values()
        )
        == 300
    )


def test_ineligible_flank_is_rejected_without_mutation() -> None:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    before = world_hash(world)
    plan = StandingPlan(tactic=Tactic.FLANK)
    with pytest.raises(SimulationServiceError, match="flank"):
        exchange(
            world,
            scenario,
            [
                command(
                    SetPlanCommand(faction_id=ATTACKER, battle_id=BATTLE_ID, plan=plan)
                )
            ],
        )
    assert world_hash(world) == before


def test_exchange_cap_and_active_movement_lock_are_preserved() -> None:
    world, scenario = battle_fixture(casualty_rate_percent=0)
    start_battle(world, scenario)
    for _ in range(4):
        world = exchange(world, scenario).world
    assert world.battles[0].status == BattleStatus.AWAITING_NEXT_TURN
    assert armies_in_open_battle(world) == {"army_a", "army_b"}
    with pytest.raises(SimulationServiceError, match="allowance"):
        exchange(world, scenario)


def test_withdrawal_without_route_leaves_a_coherent_army_fighting() -> None:
    world, scenario = battle_fixture(casualty_rate_percent=0)
    start_battle(world, scenario)
    result = exchange(
        world,
        scenario,
        [command(WithdrawCommand(faction_id=ATTACKER, battle_id=BATTLE_ID))],
    )
    assert result.delta.battle.contingents[ATTACKER].status == ContingentStatus.FIGHTING
    assert result.world.armies["army_a"].location_id == REGION


def test_no_route_rout_surrenders_on_the_next_boundary() -> None:
    world, scenario = battle_fixture(casualty_rate_percent=0)
    world.armies["army_a"].morale = 10
    start_battle(world, scenario)
    first = exchange(world, scenario)
    assert first.delta.battle.contingents[ATTACKER].status == ContingentStatus.ROUTED
    assert first.world.prisoners == []
    second = exchange(first.world, scenario)
    assert second.delta.battle.outcome == BattleOutcome.ATTACKER_SURRENDER
    assert sum(prisoner.troop_count for prisoner in second.world.prisoners) == 1000


def test_simultaneous_successful_withdrawals_have_no_pursuit() -> None:
    world, scenario = battle_fixture(
        has_routes=True, escape_min_percent=100, escape_max_percent=100
    )
    start_battle(world, scenario)
    commands = [
        command(
            WithdrawCommand(faction_id=faction, battle_id=BATTLE_ID), identity=faction
        )
        for faction in (ATTACKER, DEFENDER)
    ]
    result = exchange(world, scenario, commands)
    assert result.world.armies["army_a"].location_id == "home_a"
    assert result.world.armies["army_b"].location_id == "home_b"
    assert all(
        not row.pursuit_losses and not row.combat_losses
        for row in result.receipt.accounting
    )
    assert result.delta.battle.outcome == BattleOutcome.MUTUAL_DISENGAGEMENT
    assert len(result.delta.retreat_proposals) == 2


def test_successful_withdrawal_applies_one_rounded_pursuit_and_stops_orders() -> None:
    world, scenario = battle_fixture(
        101, 1000, has_routes=True, escape_min_percent=100, escape_max_percent=100
    )
    start_battle(world, scenario)
    result = exchange(
        world,
        scenario,
        [command(WithdrawCommand(faction_id=ATTACKER, battle_id=BATTLE_ID))],
    )
    assert result.receipt.accounting[0].pursuit_losses == {TroopType.INFANTRY: 3}
    assert result.world.armies["army_a"].troops == {TroopType.INFANTRY: 98}
    assert result.world.armies["army_a"].march is None
    assert result.world.armies["army_a"].order is None
    assert result.delta.battle.contingents[ATTACKER].has_pursuit_resolved


def test_pressure_reserve_policy_commits_at_the_next_boundary() -> None:
    world, scenario = battle_fixture(casualty_rate_percent=0)
    start_battle(world, scenario)
    contingent = world.battles[0].contingents[ATTACKER]
    contingent.plan.reserve_policy = ReservePolicy.REINFORCE_ON_PRESSURE
    world.armies["army_a"].troops[TroopType.INFANTRY] = 800
    result = exchange(world, scenario)
    assert result.delta.battle.contingents[ATTACKER].has_committed_reserves
    assert (
        sum(
            result.delta.battle.contingents[ATTACKER]
            .deployments["army_a"]
            .active.values()
        )
        == 800
    )

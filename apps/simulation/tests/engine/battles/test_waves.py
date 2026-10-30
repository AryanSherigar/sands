import pytest
from app.engine.battles.creation import create_battle
from app.engine.battles.exchange import resolve_exchange
from app.engine.battles.reducer import reduce_wave
from app.engine.battles.state import ExchangeResult
from app.engine.battles.waves import advance_wave
from app.engine.campaign import begin_campaign
from app.engine.hashing import world_hash
from app.models.battle_command import AcceptedCommand, WithdrawCommand
from app.models.world_battle import BattleStatus, ContingentStatus, StandingPlan
from app.models.world_state import WorldState
from strategy_contracts.battle import BattleTuning, WithdrawalPolicy
from strategy_contracts.enums import RelationStatus, Terrain
from strategy_contracts.scenario import StrategyScenario

from tests.engine.battles.builders import ATTACKER, DEFENDER
from tests.engine.movement.builders import (
    make_army,
    make_map,
    make_scenario,
    make_world_for,
)


def _battle_map(has_backup: bool) -> tuple[dict[str, str], StrategyScenario]:
    regions = {"field_1": DEFENDER, "field_2": DEFENDER, "common": "house_c"}
    if has_backup:
        regions["backup"] = "house_c"
    links = [
        (field, home)
        for field in ("field_1", "field_2")
        for home in ("common", "backup")
        if home in regions
    ]
    scenario = make_scenario(
        make_map({identity: Terrain.PLAIN for identity in regions}, links)
    )
    scenario.tuning.battle = BattleTuning(
        casualty_rate_percent=1, escape_min_percent=100, escape_max_percent=100
    )
    return regions, scenario


def two_battles(has_backup: bool = True) -> tuple[WorldState, StrategyScenario]:
    regions, scenario = _battle_map(has_backup)
    armies = [
        make_army(f"army_{owner}_{index}", owner, f"field_{index}")
        for index in (1, 2)
        for owner in (ATTACKER, DEFENDER)
    ]
    statuses = {
        (ATTACKER, DEFENDER): RelationStatus.WAR,
        (ATTACKER, "house_c"): RelationStatus.ALLIANCE,
        (DEFENDER, "house_c"): RelationStatus.ALLIANCE,
    }
    world = make_world_for(regions, armies, statuses)
    for faction in world.factions.values():
        faction.is_player = True
    for index in (1, 2):
        _insert_battle(world, scenario, index)
    return begin_campaign(world, scenario).world, scenario


def _insert_battle(world: WorldState, scenario: StrategyScenario, index: int) -> None:
    battle = create_battle(
        world,
        f"field_{index}",
        [f"army_{ATTACKER}_{index}"],
        [f"army_{DEFENDER}_{index}"],
        scenario,
        f"battle_{index}",
    )
    for contingent in battle.contingents.values():
        contingent.plan = StandingPlan(withdrawal_policy=WithdrawalPolicy.HOLD_AT_COST)
    world.battles.append(battle)


def test_npc_last_point_is_reserved_globally_in_battle_order() -> None:
    world, scenario = two_battles()
    world.factions[DEFENDER].is_player = False
    world.factions[DEFENDER].orders_remaining = 1
    first = advance_wave(world, scenario, expected_turn=0, expected_wave=1)
    assert len(first.world.accepted_commands) == 1
    assert first.world.accepted_commands[0].battle_id == "battle_1"
    assert first.world.factions[DEFENDER].orders_remaining == 0
    assert [battle.total_exchanges for battle in first.world.battles] == [1, 1]
    reversed_world = world.model_copy(deep=True)
    reversed_world.battles.reverse()
    reversed_world.armies = dict(reversed(list(reversed_world.armies.items())))
    permuted = advance_wave(reversed_world, scenario, expected_turn=0, expected_wave=1)
    assert world_hash(first.world) == world_hash(permuted.world)
    assert first.events == permuted.events
    assert first.receipts == permuted.receipts


def retreat_results(
    world: WorldState, scenario: StrategyScenario
) -> list[ExchangeResult]:
    results = []
    for identity, faction_id in (("battle_1", ATTACKER), ("battle_2", DEFENDER)):
        accepted = AcceptedCommand(
            id=f"withdraw_{identity}",
            operation_id=f"withdraw_{identity}",
            actor_id="owner",
            faction_id=faction_id,
            battle_id=identity,
            accepted_turn=0,
            accepted_wave=0,
            execution_turn=0,
            execution_wave=1,
            reserved_cost=1,
            command=WithdrawCommand(faction_id=faction_id, battle_id=identity),
        )
        results.append(resolve_exchange(world, identity, scenario, [accepted], {}))
    return results


@pytest.mark.parametrize("has_backup", [True, False])
def test_hostile_retreat_claims_choose_next_route_or_fail_without_reroll(
    has_backup: bool,
) -> None:
    world, scenario = two_battles(has_backup)
    results = retreat_results(world, scenario)
    chosen = results[0].delta.retreat_proposals[0].destination_id
    assert results[1].delta.retreat_proposals[0].destination_id == chosen
    reduced, events = reduce_wave(world, results)
    reverse, reverse_events = reduce_wave(world, list(reversed(results)))
    assert world_hash(reduced) == world_hash(reverse)
    assert events == reverse_events
    first, second = reduced.battles
    assert first.contingents[ATTACKER].retreat_destination_id == chosen
    destination = second.contingents[DEFENDER].retreat_destination_id
    assert destination != chosen
    if has_backup:
        assert destination is not None
    else:
        assert destination is None
        assert second.contingents[DEFENDER].status == ContingentStatus.FIGHTING
        assert second.status == BattleStatus.AWAITING_COMMANDS


def test_reducer_never_overwrites_another_battle_or_shared_world() -> None:
    world, scenario = two_battles()
    results = [
        resolve_exchange(world, battle.id, scenario, [], {}) for battle in world.battles
    ]
    results[-1].world.factions[ATTACKER].treasury = -99999
    reduced, _ = reduce_wave(world, results)
    assert all(battle.total_exchanges == 1 for battle in reduced.battles)
    assert reduced.factions == world.factions
    for index in (1, 2):
        assert any(
            reduced.armies[f"army_{owner}_{index}"].troops
            != world.armies[f"army_{owner}_{index}"].troops
            for owner in (ATTACKER, DEFENDER)
        )


def test_new_internal_ruleset_records_wave_losses_by_owner() -> None:
    world, scenario = two_battles()
    world.internal_ruleset = 1
    results = [
        resolve_exchange(world, battle.id, scenario, [], {}) for battle in world.battles
    ]

    reduced, _ = reduce_wave(world, results)

    expected: dict[str, int] = {}
    for result in results:
        for row in result.receipt.accounting:
            owner = world.armies[row.army_id].owner_id
            losses = sum(row.combat_losses.values()) + sum(row.pursuit_losses.values())
            losses += sum(row.captives.values())
            expected[owner] = expected.get(owner, 0) + losses
    assert reduced.battle_losses == expected


def test_zero_points_does_not_block_global_advance() -> None:
    world, scenario = two_battles()
    for faction in world.factions.values():
        faction.is_player = False
        faction.orders_remaining = 0
    result = advance_wave(world, scenario, expected_turn=0, expected_wave=1)
    assert result.world.progress.completed_waves == 1
    assert result.world.accepted_commands == []


def test_receipts_record_final_arbitration_for_failed_retreat() -> None:
    from tests.engine.battles.builders import accept

    world, scenario = two_battles(has_backup=False)
    for battle_id, faction_id in (("battle_1", ATTACKER), ("battle_2", DEFENDER)):
        world = accept(
            world,
            scenario,
            WithdrawCommand(faction_id=faction_id, battle_id=battle_id),
            identity=f"withdraw_{battle_id}",
            faction=faction_id,
        ).world
    result = advance_wave(world, scenario, expected_turn=0, expected_wave=1)
    first, second = result.receipts
    assert first.retreats[0].destination_id == "common"
    assert first.retreats[0].has_succeeded
    assert second.retreats[0].destination_id is None
    assert not second.retreats[0].has_succeeded
    assert second.outcome is None


def test_shorter_configured_wave_cap_remains_awaiting_next_campaign() -> None:
    world, scenario = two_battles()
    scenario.tuning.battle.max_exchanges_per_turn = 1
    result = advance_wave(world, scenario, expected_turn=0, expected_wave=1)
    assert result.is_complete
    assert all(
        battle.status == BattleStatus.AWAITING_NEXT_TURN
        for battle in result.world.battles
    )


def test_failed_mutual_departure_reconciles_victor_and_event() -> None:
    from app.models.world_battle import BattleOutcome

    from tests.engine.battles.builders import accept

    world, scenario = two_battles(has_backup=False)
    participants = (
        ("battle_1", ATTACKER),
        ("battle_2", ATTACKER),
        ("battle_2", DEFENDER),
    )
    for battle_id, faction_id in participants:
        world = accept(
            world,
            scenario,
            WithdrawCommand(faction_id=faction_id, battle_id=battle_id),
            identity=f"withdraw_{battle_id}_{faction_id}",
            faction=faction_id,
        ).world
    result = advance_wave(world, scenario, expected_turn=0, expected_wave=1)
    assert result.world.battles[1].outcome == BattleOutcome.DEFENDER_VICTORY
    assert result.receipts[1].outcome == BattleOutcome.DEFENDER_VICTORY
    event = next(
        event
        for event in result.events
        if event.kind == "battle_exchange_resolved"
        and event.cause.subject_ids == ["battle_2"]
    )
    assert event.changes[0].after == BattleOutcome.DEFENDER_VICTORY.value


def test_failed_retreat_restores_authoritative_deployment_partition() -> None:
    from tests.engine.battles.builders import accept

    world, scenario = two_battles(has_backup=False)
    for battle_id, faction_id in (("battle_1", ATTACKER), ("battle_2", DEFENDER)):
        world = accept(
            world,
            scenario,
            WithdrawCommand(faction_id=faction_id, battle_id=battle_id),
            identity=f"withdraw_{battle_id}",
            faction=faction_id,
        ).world
    result = advance_wave(world, scenario, expected_turn=0, expected_wave=1)
    contingent = result.world.battles[1].contingents[DEFENDER]
    assert contingent.status == ContingentStatus.FIGHTING
    for army_id in contingent.army_ids:
        army = result.world.armies[army_id]
        deployment = contingent.deployments[army_id]
        assert deployment.available == army.troops
        for troop_type, count in army.troops.items():
            assert (
                deployment.active.get(troop_type, 0)
                + deployment.reserve.get(troop_type, 0)
                == count
            )
    assert result.receipts[1].output_hash == world_hash(result.world)

import pytest
from app.exceptions.base import SimulationServiceError
from app.models.battle_command import (
    CommitReservesCommand,
    SetPlanCommand,
    SurrenderCommand,
    WithdrawCommand,
)
from app.models.world_battle import StandingPlan
from strategy_contracts.battle import Formation, SupplyState, Tactic, Weather
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


def test_exact_simultaneous_arithmetic_uses_per_army_morale_and_fatigue() -> None:
    world, scenario = battle_fixture(
        100,
        100,
        formation_reserve_percent={formation: 0 for formation in Formation},
        tactic_attack_percent={tactic: 100 for tactic in Tactic},
        tactic_protection_percent={tactic: 100 for tactic in Tactic},
        random_damage_min_percent=100,
        random_damage_max_percent=100,
        supply_attack_percent={state: 100 for state in SupplyState},
        supply_extra_fatigue={state: 0 for state in SupplyState},
        weather_attack_percent={weather: 100 for weather in Weather},
    )
    for army in world.armies.values():
        army.morale = 50
    start_battle(world, scenario)
    result = exchange(world, scenario)
    for army in result.world.armies.values():
        assert army.troops == {TroopType.INFANTRY: 90}
        assert (army.morale, army.fatigue) == (39, 8)
    assert [row.combat_losses for row in result.receipt.accounting] == [
        {TroopType.INFANTRY: 10},
        {TroopType.INFANTRY: 10},
    ]


def test_supply_weather_and_fatigue_reduce_attack_and_extra_fatigue_is_consumed() -> (
    None
):
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    clear = exchange(world, scenario)
    isolated = world.model_copy(deep=True)
    isolated.battles[0].contingents[ATTACKER].supply = SupplyState.ISOLATED
    isolated.battles[0].weather = Weather.SEVERE
    isolated.armies["army_a"].fatigue = 70
    reduced = exchange(isolated, scenario)
    assert sum(reduced.receipt.accounting[1].combat_losses.values()) < sum(
        clear.receipt.accounting[1].combat_losses.values()
    )
    assert reduced.world.armies["army_a"].fatigue == 82


def test_a_new_plan_only_resets_its_own_contingent_request() -> None:
    ally = make_army("army_c", ALLY, REGION, {TroopType.INFANTRY: 1000})
    world, scenario = battle_fixture(extra_armies=[ally], casualty_rate_percent=0)
    start_battle(world, scenario)
    previous_ally_target = world.battles[0].contingents[ALLY].desired_active
    plan = StandingPlan(formation=Formation.DEFENSIVE)
    result = exchange(
        world,
        scenario,
        [command(SetPlanCommand(faction_id=ATTACKER, battle_id=BATTLE_ID, plan=plan))],
    )
    assert result.delta.battle.contingents[ATTACKER].desired_active == 600
    assert result.delta.battle.contingents[ALLY].desired_active == previous_ally_target


def test_competing_allied_commitments_split_shared_capacity() -> None:
    ally = make_army("army_c", ALLY, REGION, {TroopType.INFANTRY: 1000})
    world, scenario = battle_fixture(
        extra_armies=[ally], terrain=Terrain.MOUNTAIN, casualty_rate_percent=0
    )
    start_battle(world, scenario)
    commands = [
        command(
            CommitReservesCommand(faction_id=faction, battle_id=BATTLE_ID),
            identity=faction,
        )
        for faction in (ATTACKER, ALLY)
    ]
    result = exchange(world, scenario, commands)
    assert [
        sum(
            result.delta.battle.contingents[faction]
            .deployments[army_id]
            .active.values()
        )
        for faction, army_id in ((ATTACKER, "army_a"), (ALLY, "army_c"))
    ] == [150, 150]
    assert exchange(world, scenario, list(reversed(commands))) == result


def test_a_failed_withdrawal_does_no_ordinary_damage() -> None:
    world, scenario = battle_fixture(
        escape_min_percent=0, escape_max_percent=0, has_routes=True
    )
    start_battle(world, scenario)
    result = exchange(
        world,
        scenario,
        [command(WithdrawCommand(faction_id=ATTACKER, battle_id=BATTLE_ID))],
    )
    assert result.receipt.accounting[1].combat_losses == {}
    assert sum(result.receipt.accounting[0].combat_losses.values()) > 0
    assert result.world.armies["army_a"].location_id == REGION


def test_surrender_is_not_an_exchange_of_damage_or_strain_for_the_winner() -> None:
    world, scenario = battle_fixture()
    start_battle(world, scenario)
    result = exchange(
        world,
        scenario,
        [command(SurrenderCommand(faction_id=ATTACKER, battle_id=BATTLE_ID))],
    )
    assert result.world.armies["army_b"] == world.armies["army_b"]


def test_every_nonempty_side_fields_at_least_one_even_with_full_reserve_tuning() -> (
    None
):
    world, scenario = battle_fixture(
        formation_reserve_percent={formation: 100 for formation in Formation}
    )
    start_battle(world, scenario)
    assert (
        sum(
            world.battles[0].contingents[ATTACKER].deployments["army_a"].active.values()
        )
        == 1
    )


def test_retreat_candidates_exclude_occupied_and_hostile_routes() -> None:
    from app.engine.battles.retreat import retreat_candidates
    from app.models.world_region import OccupationState

    world, scenario = battle_fixture(has_routes=True)
    start_battle(world, scenario)
    battle = world.battles[0]
    assert retreat_candidates(
        world, battle, battle.contingents[ATTACKER], scenario
    ) == ["home_a"]
    world.regions["home_a"].occupation = OccupationState(
        occupier_id=DEFENDER, siege_progress=0
    )
    assert (
        retreat_candidates(world, battle, battle.contingents[ATTACKER], scenario) == []
    )
    world.regions["home_a"].occupation = None
    world.armies["hidden_enemy"] = make_army("hidden_enemy", DEFENDER, "home_a")
    assert (
        retreat_candidates(world, battle, battle.contingents[ATTACKER], scenario) == []
    )


def test_battle_creation_is_pure_and_rejects_reusing_engaged_armies() -> None:
    from app.engine.battles.creation import create_battle

    world, scenario = battle_fixture()
    before = world.model_dump()
    created = create_battle(world, REGION, ["army_a"], ["army_b"], scenario)
    assert world.model_dump() == before
    world.battles.append(created)
    with pytest.raises(SimulationServiceError, match="engaged"):
        create_battle(world, REGION, ["army_a"], ["army_b"], scenario)


def test_failed_opponent_withdrawal_still_accepts_surrender() -> None:
    world, scenario = battle_fixture(
        has_routes=True, escape_min_percent=0, escape_max_percent=0
    )
    start_battle(world, scenario)
    commands = [
        command(SurrenderCommand(faction_id=ATTACKER, battle_id=BATTLE_ID)),
        command(
            WithdrawCommand(faction_id=DEFENDER, battle_id=BATTLE_ID),
            identity="withdraw",
        ),
    ]
    result = exchange(world, scenario, commands)
    assert "army_a" not in result.world.armies
    assert sum(prisoner.troop_count for prisoner in result.world.prisoners) == 1000


def test_a_failed_voluntary_withdrawal_cannot_suppress_forced_rout() -> None:
    from app.models.world_battle import ContingentStatus

    world, scenario = battle_fixture(casualty_rate_percent=0)
    world.armies["army_a"].morale = 10
    start_battle(world, scenario)
    result = exchange(
        world,
        scenario,
        [command(WithdrawCommand(faction_id=ATTACKER, battle_id=BATTLE_ID))],
    )
    assert result.delta.battle.contingents[ATTACKER].status == ContingentStatus.ROUTED


def test_invalid_capture_support_command_is_not_silently_marked_applied() -> None:
    from app.models.battle_command import CaptureDecisionCommand
    from app.models.battle_intelligence import CaptureDecision

    world, scenario = battle_fixture()
    start_battle(world, scenario)
    capture = command(
        CaptureDecisionCommand(
            faction_id=ATTACKER,
            battle_id=BATTLE_ID,
            capture_id="missing_capture",
            decision=CaptureDecision.RELEASE,
        )
    )
    with pytest.raises(SimulationServiceError, match="capture decision is unavailable"):
        exchange(world, scenario, [capture])


@pytest.mark.parametrize(
    "plan_id,commit_id", [("a_plan", "z_commit"), ("z_plan", "a_commit")]
)
def test_plan_and_explicit_commit_apply_in_semantic_order(
    plan_id: str, commit_id: str
) -> None:
    world, scenario = battle_fixture(casualty_rate_percent=0)
    start_battle(world, scenario)
    plan = StandingPlan(formation=Formation.DEFENSIVE)
    commands = [
        command(
            SetPlanCommand(faction_id=ATTACKER, battle_id=BATTLE_ID, plan=plan),
            identity=plan_id,
        ),
        command(
            CommitReservesCommand(faction_id=ATTACKER, battle_id=BATTLE_ID),
            identity=commit_id,
        ),
    ]
    result = exchange(world, scenario, commands)
    contingent = result.delta.battle.contingents[ATTACKER]
    assert contingent.plan == plan
    assert contingent.has_committed_reserves
    assert sum(contingent.deployments["army_a"].active.values()) == 1000
    assert exchange(world, scenario, list(reversed(commands))) == result


@pytest.mark.parametrize(
    "surrendering,winner,winner_army,outcome",
    [
        (ATTACKER, DEFENDER, "army_b", "attacker_surrender"),
        (DEFENDER, ATTACKER, "army_a", "defender_surrender"),
    ],
)
@pytest.mark.parametrize("winner_morale", [10, 15])
def test_surrender_outcome_prevents_automatic_winner_departure(
    surrendering: str, winner: str, winner_army: str, outcome: str, winner_morale: int
) -> None:
    from app.models.world_battle import ContingentStatus

    world, scenario = battle_fixture(
        has_routes=True,
        casualty_rate_percent=0,
        escape_min_percent=100,
        escape_max_percent=100,
    )
    world.armies[winner_army].morale = winner_morale
    start_battle(world, scenario)
    result = exchange(
        world,
        scenario,
        [command(SurrenderCommand(faction_id=surrendering, battle_id=BATTLE_ID))],
    )
    assert result.is_terminal
    assert result.delta.battle.outcome == outcome
    assert result.receipt.outcome == outcome
    assert result.delta.battle.contingents[winner].status == ContingentStatus.FIGHTING
    assert result.world.armies[winner_army].location_id == REGION
    assert result.delta.retreat_proposals == []
    assert sum(prisoner.troop_count for prisoner in result.world.prisoners) == 1000

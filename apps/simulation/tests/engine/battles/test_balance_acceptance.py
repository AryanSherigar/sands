from dataclasses import dataclass

from app.engine.battles.exchange import resolve_exchange
from app.engine.campaign import advance_campaign, begin_campaign
from app.models.world_battle import BattleOutcome, BattleState, BattleStatus
from app.models.world_state import WorldState
from hypothesis import given, settings
from hypothesis import strategies as st
from strategy_contracts.enums import Terrain
from strategy_contracts.scenario import StrategyScenario

from tests.engine.battles.builders import BATTLE_ID, battle_fixture, start_battle

SEED_COUNT = 100
MAX_EXCHANGES_PER_FIXTURE = 40


@dataclass(frozen=True)
class BalanceResult:
    winner: str
    exchanges: int
    attacker_losses: int
    defender_losses: int


@given(seed=st.integers(min_value=0, max_value=2**32 - 1))
@settings(max_examples=40, deadline=None)
def test_exchange_replay_matches_after_world_document_restore(seed: int) -> None:
    world, scenario = battle_fixture()
    world.rng.seed = seed
    start_battle(world, scenario)
    world = begin_campaign(world, scenario).world
    world = advance_campaign(
        world, scenario, expected_turn=0, expected_wave=1
    ).result.world
    checkpoint = advance_campaign(
        world, scenario, expected_turn=0, expected_wave=2
    ).result.world
    restored = WorldState.model_validate(checkpoint.model_dump(mode="json"))
    uninterrupted = _finish_campaign(checkpoint, scenario)
    replayed = _finish_campaign(restored, scenario)
    assert replayed == uninterrupted


def _finish_campaign(world: WorldState, scenario: StrategyScenario) -> WorldState:
    for wave in (3, 4):
        world = advance_campaign(
            world, scenario, expected_turn=world.clock.turn, expected_wave=wave
        ).result.world
    return world


def test_one_hundred_seed_balance_scenarios_are_deterministic_and_reportable() -> None:
    fixtures = (
        ("equal_plain", 1000, 1000, Terrain.PLAIN),
        ("ten_to_one_plain", 10000, 1000, Terrain.PLAIN),
        ("small_mountain_defense", 10000, 1000, Terrain.MOUNTAIN),
    )
    measured = {
        name: [
            _run_fixture(attacker, defender, terrain, seed)
            for seed in range(SEED_COUNT)
        ]
        for name, attacker, defender, terrain in fixtures
    }
    assert all(len(results) == SEED_COUNT for results in measured.values())
    assert all(
        _run_fixture(attacker, defender, terrain, seed) == measured[name][seed]
        for name, attacker, defender, terrain in fixtures
        for seed in range(SEED_COUNT)
    )
    plain_wins = sum(
        result.winner == "attacker" for result in measured["ten_to_one_plain"]
    )
    assert plain_wins >= 95


def _run_fixture(
    attacker: int, defender: int, terrain: Terrain, seed: int
) -> BalanceResult:
    world, scenario = battle_fixture(attacker, defender, terrain)
    world.rng.seed = seed
    start_battle(world, scenario)
    initial_attacker = attacker
    initial_defender = defender
    for _ in range(MAX_EXCHANGES_PER_FIXTURE):
        battle = world.battles[0]
        if battle.status == BattleStatus.RESOLVED:
            break
        _open_next_campaign_exchange(world, battle)
        world = resolve_exchange(world, BATTLE_ID, scenario, [], {}).world
    return _result(world, initial_attacker, initial_defender)


def _open_next_campaign_exchange(world: WorldState, battle: BattleState) -> None:
    if battle.exchanges_used == 4:
        world.clock.turn += 1
        battle.current_turn = world.clock.turn
        battle.exchanges_used = 0


def _result(world: WorldState, attacker: int, defender: int) -> BalanceResult:
    battle = world.battles[0]
    remaining_attacker = sum(
        sum(army.troops.values())
        for army in world.armies.values()
        if army.owner_id == "house_a"
    )
    remaining_defender = sum(
        sum(army.troops.values())
        for army in world.armies.values()
        if army.owner_id == "house_b"
    )
    return BalanceResult(
        winner=_winner(battle.outcome),
        exchanges=battle.total_exchanges,
        attacker_losses=attacker - remaining_attacker,
        defender_losses=defender - remaining_defender,
    )


def _winner(outcome: BattleOutcome | None) -> str:
    if outcome in (BattleOutcome.ATTACKER_VICTORY, BattleOutcome.DEFENDER_SURRENDER):
        return "attacker"
    if outcome in (BattleOutcome.DEFENDER_VICTORY, BattleOutcome.ATTACKER_SURRENDER):
        return "defender"
    if outcome is None:
        return "unresolved"
    return "mutual_disengagement"

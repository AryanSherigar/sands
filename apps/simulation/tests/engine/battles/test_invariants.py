from app.engine.hashing import world_hash
from app.models.world_state import WorldState
from hypothesis import given, settings
from hypothesis import strategies as st
from strategy_contracts.enums import Terrain, TroopType

from tests.engine.battles.builders import (
    ALLY,
    ATTACKER,
    REGION,
    battle_fixture,
    exchange,
    start_battle,
)
from tests.engine.movement.builders import make_army


@given(
    attacker=st.integers(min_value=1, max_value=20000),
    defender=st.integers(min_value=1, max_value=20000),
    cavalry=st.integers(min_value=0, max_value=1000),
    ally=st.integers(min_value=1, max_value=2000),
    seed=st.integers(min_value=0, max_value=2**32),
    terrain=st.sampled_from(list(Terrain)),
)
@settings(max_examples=100, deadline=None)
def test_conservation_bounds_frontage_and_permutation(
    attacker: int, defender: int, cavalry: int, ally: int, seed: int, terrain: Terrain
) -> None:
    allied_army = make_army("army_c", ALLY, REGION, {TroopType.INFANTRY: ally})
    world, scenario = battle_fixture(
        attacker, defender, terrain, extra_armies=[allied_army]
    )
    world.armies["army_a"].troops[TroopType.CAVALRY] = cavalry
    world.rng.seed = seed
    start_battle(world, scenario)
    before = world_hash(world)
    result = exchange(world, scenario)
    assert world_hash(world) == before
    assert WorldState.model_validate(result.world.model_dump()) == result.world
    for row in result.receipt.accounting:
        for troop_type, count in row.before.items():
            assert count == sum(
                getattr(row, field).get(troop_type, 0)
                for field in (
                    "survivors",
                    "combat_losses",
                    "pursuit_losses",
                    "captives",
                )
            )
            assert row.combat_losses.get(troop_type, 0) <= world.battles[0].contingents[
                world.armies[row.army_id].owner_id
            ].deployments[row.army_id].active.get(troop_type, 0)
    for side in ("attacker", "defender"):
        deployments = [
            deployment
            for contingent in result.delta.battle.contingents.values()
            if contingent.side == side
            for deployment in contingent.deployments.values()
        ]
        assert (
            sum(sum(deployment.active.values()) for deployment in deployments)
            <= scenario.tuning.battle.frontage[terrain]
        )
        for deployment in deployments:
            for troop_type, count in deployment.available.items():
                assert (
                    deployment.active[troop_type] + deployment.reserve[troop_type]
                    == count
                )
    permuted = world.model_copy(deep=True)
    permuted.armies = dict(reversed(list(permuted.armies.items())))
    permuted.battles[0].contingents = dict(
        reversed(list(permuted.battles[0].contingents.items()))
    )
    assert exchange(permuted, scenario) == result


def test_delta_excludes_unrelated_armies_and_shared_counters() -> None:
    world, scenario = battle_fixture()
    world.armies["unrelated"] = make_army("unrelated", ATTACKER, "home_a")
    start_battle_without_unrelated = world.armies.pop("unrelated")
    start_battle(world, scenario)
    world.armies["unrelated"] = start_battle_without_unrelated
    result = exchange(world, scenario)
    assert set(result.delta.army_updates) <= {"army_a", "army_b"}
    assert result.world.armies["unrelated"] == world.armies["unrelated"]
    assert (
        not {"counters", "factions", "clock", "world"}
        & result.delta.model_dump().keys()
    )

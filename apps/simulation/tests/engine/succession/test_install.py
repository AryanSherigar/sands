from app.engine.diplomacy.grounds import grant_ground
from app.engine.succession.heirs import find_heir_setup, regent_id_for
from app.engine.succession.install import CAUSE_EVENT, kill_ruler
from app.models.world_diplomacy import TruceState
from app.models.world_state import WorldState
from strategy_contracts.diplomacy import GroundKind
from strategy_contracts.peace import PeaceTier
from strategy_contracts.pressure import ShockKind
from strategy_contracts.scenario import StrategyScenario
from strategy_contracts.succession import HeirSetup

from tests.engine.succession.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    leader_of,
    make_succession_world,
)

HEIR_TRAITS = ["cruel", "proud"]


def _with_heir(
    world: WorldState,
    faction_id: str,
    age: int = 30,
    trait_ids: list[str] | None = None,
    grandchild: HeirSetup | None = None,
) -> StrategyScenario:
    scenario = SCENARIO.model_copy(deep=True)
    leader_id = world.factions[faction_id].leader_id
    leader = next(item for item in scenario.leaders if item.id == leader_id)
    leader.heir = HeirSetup(
        id=f"heir_of_{faction_id}",
        name="The Heir",
        trait_ids=trait_ids or HEIR_TRAITS,
        ambition_ids=[leader.ambition_ids[0]],
        age=age,
        history="Raised at court.",
        heir=grandchild,
    )
    return scenario


def _signed_truce(world: WorldState, first: str, second: str) -> TruceState:
    low, high = sorted((first, second))
    truce = TruceState(
        id="truce_1",
        faction_a=low,
        faction_b=high,
        expires_turn=world.clock.turn + 50,
        signed_turn=world.clock.turn,
        tier=PeaceTier.GENERATION,
        signatory_leader_ids=[
            world.factions[low].leader_id,
            world.factions[high].leader_id,
        ],
    )
    world.truces.append(truce)
    return truce


def test_find_heir_setup_walks_nested_heirs() -> None:
    world = make_succession_world()
    grandchild = HeirSetup(id="heir_grand", name="Grand", trait_ids=HEIR_TRAITS)
    scenario = _with_heir(world, CAUTIOUS_RIVAL, grandchild=grandchild)
    leader_id = world.factions[CAUTIOUS_RIVAL].leader_id

    assert find_heir_setup(scenario, leader_id).id == f"heir_of_{CAUTIOUS_RIVAL}"
    assert find_heir_setup(scenario, f"heir_of_{CAUTIOUS_RIVAL}").id == "heir_grand"
    assert find_heir_setup(scenario, "heir_grand") is None


def test_heir_takes_seat_with_own_traits_and_empty_opinions() -> None:
    world = make_succession_world()
    scenario = _with_heir(world, CAUTIOUS_RIVAL)
    old = leader_of(world, CAUTIOUS_RIVAL)

    kill_ruler(world, scenario, CAUTIOUS_RIVAL, "illness")

    new = leader_of(world, CAUTIOUS_RIVAL)
    assert new.id == f"heir_of_{CAUTIOUS_RIVAL}"
    assert new.trait_ids == HEIR_TRAITS
    assert new.opinions == {} and new.memories == []
    assert old.is_alive is False and old.id in world.leaders
    assert world.succession.crises == []


def test_no_heir_installs_regent_and_crisis() -> None:
    world = make_succession_world()
    tuning = SCENARIO.tuning.succession

    kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, "illness")

    regent = leader_of(world, CAUTIOUS_RIVAL)
    assert regent.id == regent_id_for(CAUTIOUS_RIVAL)
    assert regent.trait_ids == tuning.regent_trait_ids
    assert regent.age == tuning.regent_age
    (crisis,) = world.succession.crises
    assert crisis.faction_id == CAUTIOUS_RIVAL
    assert crisis.is_penalty_active is True
    assert crisis.ends_turn == world.clock.turn + tuning.crisis_turns
    assert crisis.heir_id is None


def test_minor_heir_installs_regent_without_penalty() -> None:
    world = make_succession_world()
    scenario = _with_heir(world, CAUTIOUS_RIVAL, age=10)
    tuning = SCENARIO.tuning.succession

    kill_ruler(world, scenario, CAUTIOUS_RIVAL, "illness")

    assert leader_of(world, CAUTIOUS_RIVAL).id == regent_id_for(CAUTIOUS_RIVAL)
    (crisis,) = world.succession.crises
    assert crisis.is_penalty_active is False
    assert crisis.heir_id == f"heir_of_{CAUTIOUS_RIVAL}"
    years_left = tuning.coming_of_age - 10
    assert crisis.heir_comes_of_age_turn == world.clock.turn + years_left * 6


def test_grounds_pass_to_new_leader_at_heir_percent() -> None:
    world = make_succession_world()
    scenario = _with_heir(world, CAUTIOUS_RIVAL)
    ground = grant_ground(
        world,
        scenario,
        kind=GroundKind.CLAIM,
        holder_faction_id=CAUTIOUS_RIVAL,
        target_faction_id=PLAYER,
        region_id=next(iter(world.regions)),
        strength=80,
    )
    ground.since_turn = world.clock.turn

    kill_ruler(world, scenario, CAUTIOUS_RIVAL, "illness")

    assert ground.holder_leader_id == f"heir_of_{CAUTIOUS_RIVAL}"
    assert ground.strength == 80 * scenario.tuning.diplomacy.heir_claim_percent // 100


def test_treaties_signed_by_dead_ruler_lapse() -> None:
    world = make_succession_world()
    truce = _signed_truce(world, PLAYER, CAUTIOUS_RIVAL)
    dead_id = world.factions[CAUTIOUS_RIVAL].leader_id

    kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, "illness")

    assert [lapse.truce_id for lapse in world.peace.lapses] == [truce.id]
    assert world.peace.lapses[0].leader_id == dead_id


def test_kill_ruler_is_a_noop_when_the_seat_holder_is_already_dead() -> None:
    world = make_succession_world()
    leader_of(world, CAUTIOUS_RIVAL).is_alive = False
    before = world.model_dump(mode="json")

    assert kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, "illness") == []
    assert world.model_dump(mode="json") == before


def test_ruler_died_shock_recorded_per_war() -> None:
    world = make_succession_world()
    add_war(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, "war_1")
    add_war(world, CAUTIOUS_RIVAL, PLAYER, "war_2")

    kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, "illness")

    shocks = {
        (shock.war_id, shock.faction_id)
        for shock in world.pressure.shocks
        if shock.kind is ShockKind.RULER_DIED
    }
    assert shocks == {("war_1", CAUTIOUS_RIVAL), ("war_2", CAUTIOUS_RIVAL)}


def test_events_name_the_death_cause_and_the_succession() -> None:
    world = make_succession_world()

    events = kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, CAUSE_EVENT)

    kinds = [event.kind for event in events]
    assert "ruler_died" in kinds and "ruler_succeeded" in kinds
    died = next(event for event in events if event.kind == "ruler_died")
    assert CAUSE_EVENT in died.cause.subject_ids


def test_ruleset_zero_worlds_are_left_alone() -> None:
    world = make_succession_world()
    world.succession_ruleset = 0
    before = leader_of(world, CAUTIOUS_RIVAL).id

    assert kill_ruler(world, SCENARIO, CAUTIOUS_RIVAL, "illness") == []
    assert leader_of(world, CAUTIOUS_RIVAL).id == before


def test_the_players_ruler_cannot_be_killed() -> None:
    world = make_succession_world()
    scenario = _with_heir(world, PLAYER)
    before = world.model_dump(mode="json")

    assert kill_ruler(world, scenario, PLAYER, "illness") == []
    assert world.model_dump(mode="json") == before

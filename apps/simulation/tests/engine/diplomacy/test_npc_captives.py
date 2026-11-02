from app.engine.diplomacy.npc_captives import act_on_player_captives
from app.engine.diplomacy.phase import TimePhase
from app.engine.diplomacy.prisoners import (
    PRISONER_EXECUTED,
    PRISONER_RELEASED,
)
from app.engine.pressure.mercy import mercy_total
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from strategy_contracts.enums import TroopType

from tests.engine.diplomacy.builders import run_phase, set_traits
from tests.engine.peace.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

HOLDER = WRATHFUL_RIVAL
TUNING = SCENARIO.tuning.peace


def _captive(world, prisoner_id: str = "prisoner_1", held_since: int = 0):
    prisoner = PrisonerState(
        id=prisoner_id,
        held_by_id=HOLDER,
        origin_faction_id=PLAYER,
        kind=PrisonerKind.TROOPS,
        troop_count=100,
        origin_battle_id="battle_1",
        troops_by_type={TroopType.INFANTRY: 100},
        held_since_turn=held_since,
    )
    world.prisoners.append(prisoner)
    return prisoner


def _world(traits: list[str], held_for: int):
    world = make_world()
    set_traits(world, HOLDER, traits)
    world.clock.turn = held_for
    _captive(world)
    return world


def _kinds(events) -> list[str]:
    return [event.kind for event in events]


def test_a_cruel_ruler_executes_a_captive_held_long_enough() -> None:
    world = _world(["cruel"], TUNING.npc_execute_min_hold_turns)

    events = act_on_player_captives(world, SCENARIO)

    assert _kinds(events) == [PRISONER_EXECUTED]
    assert world.prisoners == []


def test_a_cruel_ruler_waits_before_a_fresh_captive() -> None:
    world = _world(["cruel"], TUNING.npc_execute_min_hold_turns - 1)

    assert act_on_player_captives(world, SCENARIO) == []
    assert len(world.prisoners) == 1


def test_execution_costs_the_holder_and_rallies_the_players_realm() -> None:
    world = _world(["cruel"], TUNING.npc_execute_min_hold_turns)
    world.factions[PLAYER].stability = 50
    reputation = world.factions[HOLDER].reputation

    act_on_player_captives(world, SCENARIO)

    assert world.factions[HOLDER].reputation < reputation
    assert world.factions[PLAYER].stability == 50 + TUNING.martyr_stability_rally


def test_an_honorable_ruler_frees_a_captive_in_peacetime() -> None:
    world = _world(["honorable"], TUNING.npc_release_min_hold_turns)

    events = act_on_player_captives(world, SCENARIO)

    assert _kinds(events) == [PRISONER_RELEASED]
    assert world.prisoners == []


def test_an_honorable_ruler_at_war_and_confident_keeps_the_captive() -> None:
    world = _world(["honorable"], TUNING.npc_release_min_hold_turns)
    world.pressure_ruleset = 1
    add_war(world, HOLDER, PLAYER)

    assert act_on_player_captives(world, SCENARIO) == []


def test_an_npc_release_eases_the_players_will_and_earns_the_holder_standing() -> None:
    world = _world(["honorable"], TUNING.npc_release_min_hold_turns)
    world.pressure_ruleset = 1
    add_war(world, HOLDER, PLAYER)
    set_traits(world, PLAYER, ["honorable"])
    scenario = SCENARIO.model_copy(
        update={
            "tuning": SCENARIO.tuning.model_copy(
                update={
                    "overtures": SCENARIO.tuning.overtures.model_copy(
                        update={"peace_offer_max_will": 100}
                    )
                }
            )
        }
    )
    reputation = world.factions[HOLDER].reputation

    act_on_player_captives(world, scenario)

    assert world.factions[HOLDER].reputation == reputation + (
        TUNING.release_reputation_gain
    )
    assert mercy_total(world, scenario, PLAYER) > 0


def test_an_ordinary_ruler_neither_frees_nor_kills() -> None:
    world = _world(["pragmatic"], TUNING.npc_execute_min_hold_turns + 10)

    assert act_on_player_captives(world, SCENARIO) == []
    assert len(world.prisoners) == 1


def test_only_the_longest_held_captive_is_decided_each_turn() -> None:
    world = make_world()
    set_traits(world, HOLDER, ["cruel"])
    world.clock.turn = 20
    _captive(world, "prisoner_old", held_since=1)
    _captive(world, "prisoner_new", held_since=10)

    act_on_player_captives(world, SCENARIO)

    assert [item.id for item in world.prisoners] == ["prisoner_new"]


def test_the_time_phase_runs_the_decision() -> None:
    world = _world(["cruel"], TUNING.npc_execute_min_hold_turns)

    result = run_phase(TimePhase(), world)

    assert result.world.prisoners == []


def test_legacy_peace_ruleset_leaves_captives_alone() -> None:
    world = _world(["cruel"], TUNING.npc_execute_min_hold_turns + 5)
    world.peace_ruleset = 1

    result = run_phase(TimePhase(), world)

    assert len(result.world.prisoners) == 1


def _small_captive(world) -> None:
    world.prisoners[0].troop_count = 10
    world.prisoners[0].troops_by_type = {TroopType.INFANTRY: 10}


def test_a_calculating_ruler_keeps_captives_while_they_still_hurt_the_player() -> None:
    world = _world(["cruel", "cunning"], TUNING.npc_execute_min_hold_turns)

    assert act_on_player_captives(world, SCENARIO) == []
    assert len(world.prisoners) == 1


def test_a_calculating_ruler_acts_once_the_leverage_is_spent() -> None:
    world = _world(["cruel", "cunning"], TUNING.npc_execute_min_hold_turns)
    _small_captive(world)

    events = act_on_player_captives(world, SCENARIO)

    assert _kinds(events) == [PRISONER_EXECUTED]


def test_a_cruel_ruler_without_a_calculating_streak_ignores_leverage() -> None:
    world = _world(["cruel"], TUNING.npc_execute_min_hold_turns)

    assert _kinds(act_on_player_captives(world, SCENARIO)) == [PRISONER_EXECUTED]

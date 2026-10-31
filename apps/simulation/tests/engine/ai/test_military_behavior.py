from app.engine.ai.planner import plan_ai_orders
from app.engine.campaign import begin_campaign
from app.engine.hashing import world_hash
from app.engine.replay import replay_history
from app.models.battle_progress import OperationGuard
from app.models.replay import BeginCampaignReplayInput, ReplayStep, ReplayStepKind
from app.models.world_character import OpinionReason, OpinionState
from app.models.world_diplomacy import RelationState, WarState
from app.models.world_region import RegionIntel
from strategy_contracts.enums import RelationStatus

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYTHROUGH_ID,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_traits,
)

BIG = "army_carrow_1"
SMALL = "army_carrow_2"


def _world(traits: list[str] | None = None, war: bool = False):
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, traits or [])
    world.factions[CAUTIOUS_RIVAL].stance.option_id = "revenge_on_player"
    world.factions[WRATHFUL_RIVAL].leader_id = None
    valdren = world.factions[CAUTIOUS_RIVAL].leader_id
    world.leaders[valdren].opinions[
        world.factions[WRATHFUL_RIVAL].leader_id or "harl"
    ] = OpinionState(
        target_id="harl",
        reasons=[OpinionReason(cause="old feud", value=-40, fade_per_turn=0)],
    )
    if war:
        low, high = sorted((CAUTIOUS_RIVAL, WRATHFUL_RIVAL))
        world.relations = [
            RelationState(
                faction_a=low, faction_b=high, status=RelationStatus.WAR, since_turn=0
            )
        ]
        world.wars.append(
            WarState(
                id="war_1",
                attacker_id=CAUTIOUS_RIVAL,
                defender_id=WRATHFUL_RIVAL,
                started_turn=0,
            )
        )
    return world


def _moves(plan) -> dict[str, str]:
    return {
        item.command.army_id: item.command.to_region_id
        for item in plan.world.accepted_commands
        if item.faction_id == CAUTIOUS_RIVAL and item.command.kind == "move_army"
    }


def test_a_grudge_without_war_masses_armies_on_the_border() -> None:
    plan = plan_ai_orders(_world(), SCENARIO)

    assert plan.world.aims[CAUTIOUS_RIVAL].target_faction_id == WRATHFUL_RIVAL
    assert "high_meadow" in _moves(plan).values()
    assert not [
        item
        for item in plan.world.accepted_commands
        if item.command.kind in ("attack", "declare_war")
    ]


def test_at_war_armies_march_toward_the_enemy() -> None:
    plan = plan_ai_orders(_world(war=True), SCENARIO)

    assert set(_moves(plan).values()) <= {"fenwatch", "high_meadow", "kings_ford"}
    assert _moves(plan)


def test_cunning_ruler_sends_two_armies_to_different_objectives() -> None:
    world = _world(["treacherous"], war=True)
    world.factions[CAUTIOUS_RIVAL].intel["dunwick"] = RegionIntel(
        last_seen_turn=0, owner_id=WRATHFUL_RIVAL, garrison_low=40, garrison_high=60
    )

    moves = _moves(plan_ai_orders(world, SCENARIO))

    assert moves[BIG] == "dunwick"
    assert moves[SMALL] == "fenwatch"


def _commands(world) -> list[str]:
    plan = plan_ai_orders(world, SCENARIO)
    return [
        item.command.model_dump_json()
        for item in plan.world.accepted_commands
        if item.faction_id == CAUTIOUS_RIVAL
    ]


def test_planning_ignores_changes_inside_the_fog() -> None:
    world = _world(war=True)
    baseline = _commands(world)
    world.regions["brennmoor"].owner_id = WRATHFUL_RIVAL
    world.armies["army_dunwick_1"].location_id = "brennmoor"
    world.armies["army_ashford_2"].location_id = "aldgate"
    world.regions["dunwick"].garrison = 999

    assert _commands(world) == baseline


def _begin_step(before, after) -> ReplayStep:
    guard = OperationGuard(
        operation_id="begin", expected_world_version=1, expected_turn=0, expected_wave=0
    )
    return ReplayStep(
        playthrough_id=PLAYTHROUGH_ID,
        sequence=1,
        operation_id="begin",
        kind=ReplayStepKind.BEGIN_CAMPAIGN,
        input=BeginCampaignReplayInput(guard=guard, stances=[]),
        before_hash=world_hash(before),
        after_hash=world_hash(after),
        turn=0,
        wave=0,
    )


def test_marching_orders_are_applied_and_replay_to_the_same_hash() -> None:
    before = _world(war=True)
    after = begin_campaign(before.model_copy(deep=True), SCENARIO).world

    moved = [
        army
        for army in after.armies.values()
        if army.owner_id == CAUTIOUS_RIVAL
        and (
            army.march is not None
            or (
                army.id in before.armies
                and army.location_id != before.armies[army.id].location_id
            )
        )
    ]
    replayed = replay_history(before, SCENARIO, [_begin_step(before, after)])

    assert moved
    assert replayed.world_hash == world_hash(after)

from app.engine.ai.planner import plan_ai_orders
from app.engine.campaign import begin_campaign
from app.engine.hashing import world_hash
from app.engine.replay import replay_history
from app.models.battle_progress import OperationGuard
from app.models.replay import BeginCampaignReplayInput, ReplayStep, ReplayStepKind
from app.models.world_diplomacy import WarState
from strategy_contracts.enums import PayLevel

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYTHROUGH_ID,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
    set_traits,
)


def _world(stance: str, treasury: int = 100):
    world = make_world()
    set_traits(world, CAUTIOUS_RIVAL, [])
    world.factions[CAUTIOUS_RIVAL].stance.option_id = stance
    world.factions[CAUTIOUS_RIVAL].treasury = treasury
    world.factions[WRATHFUL_RIVAL].leader_id = None
    return world


def _kinds(plan) -> list[str]:
    return sorted(
        item.command.kind
        for item in plan.world.accepted_commands
        if item.faction_id == CAUTIOUS_RIVAL
    )


def _war(world) -> None:
    world.wars.append(
        WarState(
            id="war_1",
            attacker_id=WRATHFUL_RIVAL,
            defender_id=CAUTIOUS_RIVAL,
            started_turn=0,
        )
    )


def test_poor_hoarder_borrows_and_trims_pay() -> None:
    plan = plan_ai_orders(_world("turtle", treasury=10), SCENARIO)

    kinds = _kinds(plan)

    assert "take_loan" in kinds
    assert "set_pay" in kinds


def test_martial_ruler_at_war_raises_an_army() -> None:
    world = _world("revenge_on_player")
    _war(world)

    plan = plan_ai_orders(world, SCENARIO)

    assert "raise_army" in _kinds(plan)
    assert plan.world.aims[CAUTIOUS_RIVAL].target_faction_id == WRATHFUL_RIVAL


def test_rebuilding_ruler_in_peace_raises_no_army() -> None:
    plan = plan_ai_orders(_world("rebuild"), SCENARIO)

    assert "raise_army" not in _kinds(plan)


def test_comfortable_peaceful_faction_neither_borrows_nor_disbands() -> None:
    plan = plan_ai_orders(_world("rebuild", treasury=500), SCENARIO)

    assert not {"take_loan", "disband_army"} & set(_kinds(plan))


def test_planned_levy_is_raised_when_the_turn_runs() -> None:
    world = _world("revenge_on_player")
    _war(world)
    before = len(world.armies)

    result = begin_campaign(world, SCENARIO)

    assert len(result.world.armies) > before


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


def test_replay_reproduces_a_home_life_turn() -> None:
    before = _world("turtle", treasury=10)
    _war(before)
    after = begin_campaign(before.model_copy(deep=True), SCENARIO).world

    replayed = replay_history(before, SCENARIO, [_begin_step(before, after)])

    assert replayed.world_hash == world_hash(after)
    assert PayLevel.REDUCED in {a.pay_level for a in after.armies.values()}

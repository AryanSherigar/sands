from app.models.battle_intelligence import IntentKind, IntentSource
from strategy_contracts.battle import SupplyState, Tactic

from tests.engine.battles.builders import (
    ATTACKER,
    BATTLE_ID,
    battle_fixture,
    start_battle,
)


def test_fallback_uses_own_morale_supply_and_observed_advantage_only() -> None:
    from app.engine.battles.policy import fallback_intent
    from app.engine.battles.views import intent_briefing

    world, scenario = battle_fixture(1000, 1)
    start_battle(world, scenario)
    world.battles[0].contingents[ATTACKER].supply = SupplyState.SUPPLIED
    briefing = intent_briefing(world, BATTLE_ID, ATTACKER, scenario)
    assert fallback_intent(briefing, scenario.tuning.battle) == IntentKind.PRESS
    world.armies["army_a"].morale = 30
    assert (
        fallback_intent(
            intent_briefing(world, BATTLE_ID, ATTACKER, scenario),
            scenario.tuning.battle,
        )
        == IntentKind.PRESERVE
    )
    world.armies["army_a"].morale = 70
    world.battles[0].contingents[ATTACKER].supply = SupplyState.ISOLATED
    assert (
        fallback_intent(
            intent_briefing(world, BATTLE_ID, ATTACKER, scenario),
            scenario.tuning.battle,
        )
        == IntentKind.PRESERVE
    )


def test_policy_preserves_zero_budget_and_only_proposes_affordable_legal_commands() -> (
    None
):
    from app.engine.battles.policy import choose_instruction
    from app.engine.battles.views import intent_briefing

    world, scenario = battle_fixture()
    start_battle(world, scenario)
    world.factions[ATTACKER].orders_remaining = 0
    briefing = intent_briefing(world, BATTLE_ID, ATTACKER, scenario)
    assert (
        choose_instruction(briefing, IntentKind.PRESS, scenario.tuning.battle) is None
    )
    world.factions[ATTACKER].orders_remaining = 1
    briefing = intent_briefing(world, BATTLE_ID, ATTACKER, scenario)
    proposal = choose_instruction(briefing, IntentKind.PRESS, scenario.tuning.battle)
    assert proposal.faction_id == ATTACKER
    assert proposal.plan.tactic != Tactic.FLANK
    assert world.factions[ATTACKER].orders_remaining == 1


def test_recorded_intent_activation_and_fallback_have_stable_provenance() -> None:
    from app.engine.battles.exchange import resolve_exchange
    from app.engine.battles.policy import select_intent
    from app.engine.battles.views import intent_briefing

    world, scenario = battle_fixture(casualty_rate_percent=0)
    start_battle(world, scenario)
    briefing = intent_briefing(world, BATTLE_ID, ATTACKER, scenario)
    chosen = select_intent(briefing, scenario.tuning.battle)
    assert chosen.source == IntentSource.FALLBACK
    assert chosen.activation_wave == 1 and chosen.activation_exchange == 1
    assert chosen == select_intent(briefing, scenario.tuning.battle)
    result = resolve_exchange(world, BATTLE_ID, scenario, [], {chosen.id: chosen})
    assert result.delta.battle.contingents[ATTACKER].intent_id == chosen.id
    assert result.delta.battle_intents[chosen.id] == chosen
    assert chosen.id in result.receipt.intent_ids


def test_intent_candidates_require_matching_activation_and_observation() -> None:
    from app.engine.battles.policy import select_intent
    from app.engine.battles.views import intent_briefing

    world, scenario = battle_fixture(casualty_rate_percent=0)
    start_battle(world, scenario)
    briefing = intent_briefing(world, BATTLE_ID, ATTACKER, scenario)
    chosen = select_intent(briefing, scenario.tuning.battle)
    stale = chosen.model_copy(
        update={"activation_wave": 2, "kind": IntentKind.SURRENDER}
    )
    assert (
        select_intent(briefing, scenario.tuning.battle, stale).source
        == IntentSource.FALLBACK
    )
    candidate = chosen.model_copy(
        update={
            "kind": IntentKind.DELAY,
            "source": IntentSource.MODEL,
            "answer_id": "answer_1",
        }
    )
    assert select_intent(briefing, scenario.tuning.battle, candidate) == candidate


def test_unaffordable_standing_flank_losing_cavalry_normalizes_to_hold() -> None:
    from app.models.world_battle import StandingPlan

    from tests.engine.battles.builders import exchange

    world, scenario = battle_fixture(casualty_rate_percent=0)
    start_battle(world, scenario)
    world.factions[ATTACKER].orders_remaining = 0
    world.battles[0].contingents[ATTACKER].plan = StandingPlan(tactic=Tactic.FLANK)
    result = exchange(world, scenario)
    assert result.delta.battle.contingents[ATTACKER].plan.tactic == Tactic.HOLD
    assert result.world.factions[ATTACKER].orders_remaining == 0

from app.engine.ai.generators.court import envoy_candidates
from app.engine.ai.generators.subsidy import subsidy_candidates
from app.models.orders import CutSubsidyOrder, SendEnvoyOrder, SubsidizeOrder
from app.models.world_ai import AimState
from app.models.world_diplomacy import EnvoyState, RelationState
from app.models.world_pressure import SubsidyState
from strategy_contracts.enums import RelationStatus
from strategy_contracts.stances import ScoreCategory

from tests.engine.diplomacy.builders import set_traits
from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.ai
PRESSURE = SCENARIO.tuning.pressure
RICH = 1000


def _fight_player(world) -> None:
    low, high = sorted((CAUTIOUS_RIVAL, PLAYER))
    world.relations = [
        RelationState(
            faction_a=low, faction_b=high, status=RelationStatus.WAR, since_turn=0
        )
    ]


def _envoys(world):
    return envoy_candidates(world, SCENARIO, CAUTIOUS_RIVAL)


def test_a_war_enemy_that_is_not_the_player_gets_an_envoy() -> None:
    world = make_world()
    low, high = sorted((CAUTIOUS_RIVAL, WRATHFUL_RIVAL))
    world.relations = [
        RelationState(
            faction_a=low, faction_b=high, status=RelationStatus.WAR, since_turn=0
        )
    ]
    candidates = _envoys(world)
    assert [item.order for item in candidates] == [
        SendEnvoyOrder(faction_id=CAUTIOUS_RIVAL, target_faction_id=WRATHFUL_RIVAL)
    ]
    assert candidates[0].category is ScoreCategory.EXPAND
    assert candidates[0].base_score == TUNING.envoy_bonus + TUNING.envoy_target_bonus


def test_the_player_never_gets_an_envoy() -> None:
    world = make_world()
    _fight_player(world)
    assert _envoys(world) == []


def test_an_existing_envoy_is_not_repeated() -> None:
    world = make_world()
    world.aims[CAUTIOUS_RIVAL] = AimState(
        category=ScoreCategory.ATTACK,
        target_faction_id=WRATHFUL_RIVAL,
        chosen_turn=0,
        leader_id=world.factions[CAUTIOUS_RIVAL].leader_id,
        capital_held=True,
    )
    assert len(_envoys(world)) == 1
    world.envoys.append(
        EnvoyState(
            id="envoy_1", from_faction_id=CAUTIOUS_RIVAL, at_faction_id=WRATHFUL_RIVAL
        )
    )
    assert _envoys(world) == []


def test_a_cunning_ruler_also_sends_envoys_to_neighbours() -> None:
    plain = make_world()
    set_traits(plain, CAUTIOUS_RIVAL, [])
    sly = make_world()
    set_traits(sly, CAUTIOUS_RIVAL, ["cunning"])
    assert _envoys(plain) == []
    assert len(_envoys(sly)) == 1


def _subsidies(world, scenario=SCENARIO):
    return subsidy_candidates(world, scenario, CAUTIOUS_RIVAL)


def _prop_up_world(treasury: int = RICH):
    world = make_world()
    _fight_player(world)
    add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)
    world.factions[CAUTIOUS_RIVAL].treasury = treasury
    return world


def test_a_rich_ruler_funds_the_enemys_enemy() -> None:
    candidates = _subsidies(_prop_up_world())
    assert len(candidates) == 1
    order = candidates[0].order
    assert isinstance(order, SubsidizeOrder)
    assert order.target_faction_id == WRATHFUL_RIVAL
    assert 1 <= order.amount_per_turn <= PRESSURE.subsidy_max_per_turn
    assert candidates[0].category is ScoreCategory.ALLY
    assert candidates[0].base_score == TUNING.subsidy_bonus


def test_a_subsidy_never_leaves_the_payer_below_the_treasury_floor() -> None:
    candidates = _subsidies(_prop_up_world())
    order = candidates[0].order
    spent = order.amount_per_turn * order.turns
    assert RICH - spent >= 2 * TUNING.low_treasury


def test_a_poor_ruler_pays_nothing() -> None:
    assert _subsidies(_prop_up_world(treasury=TUNING.low_treasury)) == []


def test_the_player_is_never_a_receiver() -> None:
    world = make_world()
    _fight_player(world)
    add_war(world, attacker_id=PLAYER, defender_id=WRATHFUL_RIVAL)
    world.factions[CAUTIOUS_RIVAL].treasury = RICH
    assert all(item.order.target_faction_id != PLAYER for item in _subsidies(world))


def test_the_subsidy_toggle_disables_the_generator() -> None:
    scenario = SCENARIO.model_copy(deep=True)
    scenario.toggles.is_ai_subsidy_enabled = False
    assert _subsidies(_prop_up_world(), scenario) == []


def _paid_subsidy(world, war_id: str = "war_1") -> None:
    world.pressure.subsidies.append(
        SubsidyState(
            id="subsidy_1",
            payer_id=CAUTIOUS_RIVAL,
            receiver_id=WRATHFUL_RIVAL,
            war_id=war_id,
            expires_turn=99,
            amount_per_turn=5,
        )
    )


def test_a_poor_payer_cuts_its_subsidy() -> None:
    world = _prop_up_world(treasury=0)
    _paid_subsidy(world)
    cuts = [
        item for item in _subsidies(world) if isinstance(item.order, CutSubsidyOrder)
    ]
    assert [item.order.subsidy_id for item in cuts] == ["subsidy_1"]
    assert cuts[0].category is ScoreCategory.HOARD


def test_a_subsidy_for_an_ended_war_is_cut() -> None:
    world = _prop_up_world()
    _paid_subsidy(world, war_id="war_gone")
    assert any(isinstance(item.order, CutSubsidyOrder) for item in _subsidies(world))


def test_a_funded_subsidy_in_a_live_war_is_kept() -> None:
    world = _prop_up_world()
    _paid_subsidy(world)
    assert not any(
        isinstance(item.order, CutSubsidyOrder) for item in _subsidies(world)
    )

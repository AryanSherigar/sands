import pytest
from app.engine.diplomacy.mediation import apply_mediation
from app.engine.diplomacy.phase import DiplomacyPhase
from app.engine.diplomacy.validation import validate_mediate_order
from app.exceptions.command_exceptions import CommandError
from app.models.orders import MediateOrder
from strategy_contracts.enums import OrderKind

from tests.engine.diplomacy.builders import queue_npc_order, run_phase
from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
    set_score,
)


def _npc_war(world, war_id: str = "war_1"):
    return add_war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL, war_id)


def _order(war_id: str = "war_1", mediator: str = PLAYER) -> MediateOrder:
    return MediateOrder(faction_id=mediator, war_id=war_id)


def test_mediate_kind_has_a_default_cost() -> None:
    assert SCENARIO.tuning.order_costs[OrderKind.MEDIATE] >= 0


def test_mediate_opens_an_offer_for_a_neutral() -> None:
    world = make_world()
    war = _npc_war(world)

    events = apply_mediation(world, SCENARIO, _order(war.id))

    offer = world.pressure.mediation_offers[0]
    assert (offer.mediator_id, offer.war_id) == (PLAYER, war.id)
    assert [event.kind for event in events] == ["mediation_offered"]


def test_mediate_is_rejected_for_a_belligerent() -> None:
    world = make_world()
    war = add_war(world)

    with pytest.raises(CommandError) as error:
        validate_mediate_order(world, _order(war.id))

    assert error.value.code == "mediator_is_belligerent"


def test_mediate_is_rejected_for_a_finished_war() -> None:
    world = make_world()

    with pytest.raises(CommandError) as error:
        validate_mediate_order(world, _order("war_9"))

    assert error.value.code == "unknown_war"


def test_a_second_offer_for_the_same_war_is_rejected() -> None:
    world = make_world()
    war = _npc_war(world)
    apply_mediation(world, SCENARIO, _order(war.id))

    with pytest.raises(CommandError) as error:
        validate_mediate_order(world, _order(war.id))

    assert error.value.code == "offer_exists"


def test_a_destroyed_mediator_is_rejected() -> None:
    world = make_world()
    war = _npc_war(world)
    world.factions[PLAYER].is_destroyed = True

    with pytest.raises(CommandError) as error:
        validate_mediate_order(world, _order(war.id))

    assert error.value.code == "mediator_unavailable"


def test_player_mediation_ends_an_npc_war_in_white_peace_when_eligible() -> None:
    world = make_world()
    war = set_score(_npc_war(world), attacker=0, defender=0)
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.peace.white_peace_min_strain = 0
    scenario.negotiation.base_accept = -100

    events = apply_mediation(world, scenario, _order(war.id))

    assert world.wars == []
    assert world.truces[0].tier is not None
    assert "peace_signed" in [event.kind for event in events]


def test_player_mediation_leaves_the_war_when_not_eligible() -> None:
    world = make_world()
    war = set_score(_npc_war(world), attacker=80, defender=10)

    apply_mediation(world, SCENARIO, _order(war.id))

    assert len(world.wars) == 1


def test_mediate_order_flows_through_the_diplomacy_phase() -> None:
    world = make_world()
    war = _npc_war(world)
    world = queue_npc_order(world, SCENARIO, _order(war.id))

    result = run_phase(DiplomacyPhase(), world)

    assert len(result.world.pressure.mediation_offers) == 1

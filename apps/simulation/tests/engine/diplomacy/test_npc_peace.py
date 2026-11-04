import pytest
from app.engine.diplomacy.npc_peace import apply_sue_peace
from app.engine.diplomacy.phase import DiplomacyPhase
from app.engine.diplomacy.validation import validate_sue_peace_order
from app.exceptions.command_exceptions import CommandError
from app.models.orders import SuePeaceOrder
from strategy_contracts.enums import OrderKind

from tests.engine.diplomacy.builders import queue_npc_order, run_phase
from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
    set_score,
)

DECIDED_LEAD = 80
DECIDED_TRAIL = 10


def _scenario():
    scenario = SCENARIO.model_copy(deep=True)
    scenario.tuning.peace.white_peace_min_strain = 0
    scenario.negotiation.base_accept = -100
    return scenario


def _npc_war(world):
    return add_war(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL, "war_1")


def _order(war_id: str = "war_1", faction: str = CAUTIOUS_RIVAL) -> SuePeaceOrder:
    return SuePeaceOrder(faction_id=faction, war_id=war_id)


def test_sue_peace_kind_is_free() -> None:
    assert SCENARIO.tuning.order_costs[OrderKind.SUE_PEACE] == 0


def test_sue_peace_for_an_unknown_war_is_rejected() -> None:
    world = make_world()

    with pytest.raises(CommandError) as error:
        validate_sue_peace_order(world, _order("war_9"))

    assert error.value.code == "unknown_war"


def test_sue_peace_by_a_non_belligerent_is_rejected() -> None:
    world = make_world()
    war = _npc_war(world)

    with pytest.raises(CommandError) as error:
        validate_sue_peace_order(world, _order(war.id, faction="house_outsider"))

    assert error.value.code == "not_a_belligerent"


def test_a_stalemate_ends_in_white_peace() -> None:
    world = make_world()
    war = set_score(_npc_war(world), attacker=0, defender=0)

    events = apply_sue_peace(world, _scenario(), _order(war.id))

    assert world.wars == []
    assert events[0].kind == "peace_sued"
    assert "peace_signed" in [event.kind for event in events]


def test_the_leading_side_ends_a_decided_war_with_a_short_peace() -> None:
    world = make_world()
    war = set_score(_npc_war(world), attacker=DECIDED_LEAD, defender=DECIDED_TRAIL)

    apply_sue_peace(world, _scenario(), _order(war.id, faction=war.attacker_id))

    assert world.wars == []
    assert len(world.truces) == 1


def test_the_trailing_side_cannot_buy_peace_with_nothing() -> None:
    world = make_world()
    war = set_score(_npc_war(world), attacker=DECIDED_LEAD, defender=DECIDED_TRAIL)

    events = apply_sue_peace(
        world, _scenario(), _order(war.id, faction=war.defender_id)
    )

    assert len(world.wars) == 1
    assert [event.kind for event in events] == ["peace_refused"]


def test_a_refusing_counterpart_leaves_the_war_open() -> None:
    world = make_world()
    war = set_score(_npc_war(world), attacker=0, defender=0)
    scenario = _scenario()
    scenario.negotiation.base_accept = 1000

    events = apply_sue_peace(world, scenario, _order(war.id))

    assert len(world.wars) == 1
    assert [event.kind for event in events] == ["peace_refused"]


def test_sue_peace_flows_through_the_diplomacy_phase() -> None:
    world = make_world()
    war = _npc_war(world)
    world = queue_npc_order(world, SCENARIO, _order(war.id))

    result = run_phase(DiplomacyPhase(), world)

    kinds = {event.cause.summary_key for event in result.events}
    assert kinds & {"peace_sued", "peace_refused"}


def _collapsed_loser_world():
    world = make_world()
    war = _npc_war(world)
    set_score(war, attacker=DECIDED_TRAIL, defender=DECIDED_LEAD)
    world.peace_ruleset = 1
    loser = world.factions[CAUTIOUS_RIVAL]
    loser.stability, loser.war_exhaustion = 0, 100
    return world, war


def test_collapsed_loser_cedes_a_non_capital_region_to_end_the_war() -> None:
    from app.engine.diplomacy.collapse_settlement import collapse_cession

    world, war = _collapsed_loser_world()
    scenario = _scenario()

    cession = collapse_cession(world, scenario, war, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    assert cession is not None
    assert cession.from_faction_id == CAUTIOUS_RIVAL
    capitals = {f.capital_region_id for f in scenario.factions}
    assert cession.region_id not in capitals


def test_a_losing_house_that_has_not_collapsed_cannot_sue_successfully() -> None:
    from app.engine.diplomacy.collapse_settlement import is_collapsed

    world, _ = _collapsed_loser_world()
    world.factions[CAUTIOUS_RIVAL].stability = 50

    assert not is_collapsed(world, _scenario(), CAUTIOUS_RIVAL)

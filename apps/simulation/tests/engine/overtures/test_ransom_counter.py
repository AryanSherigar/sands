from app.engine.diplomacy.prisoners import handle_prisoner
from app.engine.negotiation import close_negotiation, opinion_of
from app.engine.overtures.arming import arm_overture
from app.engine.overtures.selection import select_overture
from app.models.orders import HandlePrisonerOrder
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from strategy_contracts.enums import TroopType
from strategy_contracts.overtures import OvertureKind
from strategy_contracts.scene import TermsResult
from strategy_contracts.terms import ReleasePrisonersTerm

from tests.engine.overtures.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

ORIGIN = WRATHFUL_RIVAL
RICH = 100000
TUNING = SCENARIO.tuning.peace


def _haggled_world():
    world = make_world()
    world.factions[ORIGIN].treasury = RICH
    world.factions[ORIGIN].stability = 100
    prisoner = PrisonerState(
        id="prisoner_1",
        held_by_id=PLAYER,
        origin_faction_id=ORIGIN,
        kind=PrisonerKind.TROOPS,
        troop_count=100,
        origin_battle_id="battle_1",
        troops_by_type={TroopType.INFANTRY: 100},
    )
    world.prisoners.append(prisoner)
    order = HandlePrisonerOrder(
        faction_id=PLAYER, prisoner_id=prisoner.id, action="ransom"
    )
    handle_prisoner(world, SCENARIO, order)
    assert world.peace.ransom_counters
    return world


def test_the_counter_comes_back_as_an_npc_overture() -> None:
    world = _haggled_world()

    assert select_overture(world, SCENARIO) == (ORIGIN, OvertureKind.RANSOM_COUNTER)


def test_arming_builds_the_counter_card_and_consumes_the_counter() -> None:
    world = _haggled_world()
    gold = world.peace.ransom_counters[0].gold

    arm_overture(world, SCENARIO)

    pending = world.progress.pending_negotiation
    assert pending is not None
    assert pending.overture.kind is OvertureKind.RANSOM_COUNTER
    term = pending.overture.card.terms[0]
    assert isinstance(term, ReleasePrisonersTerm)
    assert (term.holder_id, term.recipient_id) == (PLAYER, ORIGIN)
    assert term.ransom_gold == gold
    assert world.peace.ransom_counters == []


def test_accepting_the_counter_pays_the_player_and_frees_the_captive() -> None:
    world = _haggled_world()
    arm_overture(world, SCENARIO)
    card = world.progress.pending_negotiation.overture.card.model_copy(
        update={"is_confirmed_by_player": True}
    )
    scene_id = world.progress.pending_scene_id
    gold = card.terms[0].ransom_gold
    player_before = world.factions[PLAYER].treasury
    origin_before = world.factions[ORIGIN].treasury

    closed, _ = close_negotiation(world, SCENARIO, scene_id, card, TermsResult.AGREED)

    assert closed.prisoners == []
    assert closed.factions[PLAYER].treasury == player_before + gold
    assert closed.factions[ORIGIN].treasury == origin_before - gold


def _opinion(world) -> int:
    leader = world.leaders[world.factions[ORIGIN].leader_id]
    return opinion_of(leader, world.factions[PLAYER].leader_id)


def test_declining_a_counter_to_your_own_offer_costs_no_opinion() -> None:
    world = _haggled_world()
    arm_overture(world, SCENARIO)
    scene_id = world.progress.pending_scene_id
    before = _opinion(world)

    closed, _ = close_negotiation(world, SCENARIO, scene_id, None, TermsResult.REFUSED)

    assert len(closed.prisoners) == 1
    assert _opinion(closed) == before


def test_a_counter_expires_if_the_scene_is_not_reached() -> None:
    world = _haggled_world()
    world.clock.turn += TUNING.ransom_counter_expiry_turns + 1

    arm_overture(world, SCENARIO)

    assert world.progress.pending_negotiation is None
    assert world.peace.ransom_counters == []


def test_a_counter_lapses_when_the_captive_is_gone() -> None:
    world = _haggled_world()
    world.prisoners.clear()

    arm_overture(world, SCENARIO)

    assert world.progress.pending_negotiation is None
    assert world.peace.ransom_counters == []

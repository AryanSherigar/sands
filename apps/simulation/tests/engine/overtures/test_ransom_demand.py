import pytest
from app.engine.negotiation import close_negotiation, opinion_of
from app.engine.overtures.arming import arm_overture
from app.engine.overtures.cards import build_overture
from app.engine.overtures.selection import select_overture
from app.exceptions.command_exceptions import CampaignProgressError
from app.models.world_diplomacy import PrisonerKind, PrisonerState
from app.services.triggered_negotiation import _build_package
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

HOLDER = WRATHFUL_RIVAL
RICH = 10000
TUNING = SCENARIO.tuning.peace


def _world():
    world = make_world()
    world.factions[PLAYER].treasury = RICH
    return world


def _captive(world, prisoner_id: str = "prisoner_1", count: int = 100):
    prisoner = PrisonerState(
        id=prisoner_id,
        held_by_id=HOLDER,
        origin_faction_id=PLAYER,
        kind=PrisonerKind.TROOPS,
        troop_count=count,
        origin_battle_id="battle_1",
        troops_by_type={TroopType.INFANTRY: count},
    )
    world.prisoners.append(prisoner)
    return prisoner


def _armed_world(count: int = 100):
    world = _world()
    _captive(world, count=count)
    arm_overture(world, SCENARIO)
    return world


def test_holder_of_the_players_captives_demands_a_ransom() -> None:
    world = _world()
    _captive(world)

    assert select_overture(world, SCENARIO) == (HOLDER, OvertureKind.RANSOM_DEMAND)


def test_no_demand_when_the_player_holds_nobody() -> None:
    assert select_overture(make_world(), SCENARIO) is None


def test_no_demand_when_the_player_cannot_afford_any_captive() -> None:
    world = _world()
    _captive(world)
    world.factions[PLAYER].treasury = 0

    assert select_overture(world, SCENARIO) is None


def test_card_prices_every_affordable_captive() -> None:
    world = _world()
    _captive(world, "prisoner_1", count=100)
    _captive(world, "prisoner_2", count=50)

    overture = build_overture(world, SCENARIO, HOLDER, OvertureKind.RANSOM_DEMAND)

    assert overture.card is not None
    term = overture.card.terms[0]
    assert isinstance(term, ReleasePrisonersTerm)
    assert term.prisoner_ids == ["prisoner_1", "prisoner_2"]
    assert term.ransom_gold == 150 * TUNING.ransom_gold_per_troop


def test_card_leaves_out_captives_the_treasury_cannot_cover() -> None:
    world = _world()
    _captive(world, "prisoner_1", count=100)
    _captive(world, "prisoner_2", count=100)
    world.factions[PLAYER].treasury = 100 * TUNING.ransom_gold_per_troop

    overture = build_overture(world, SCENARIO, HOLDER, OvertureKind.RANSOM_DEMAND)

    assert overture.card is not None
    assert overture.card.terms[0].prisoner_ids == ["prisoner_1"]


def test_arming_pauses_planning_and_starts_the_cooldown() -> None:
    world = _armed_world()

    assert world.progress.pending_negotiation is not None
    assert world.progress.pending_negotiation.overture.kind is (
        OvertureKind.RANSOM_DEMAND
    )
    assert world.overture_cooldowns[HOLDER] > world.clock.turn


def test_no_second_demand_while_on_cooldown() -> None:
    world = _armed_world()
    world.progress.pending_scene_id = None
    world.progress.pending_negotiation = None

    assert select_overture(world, SCENARIO) is None


def test_accepting_pays_the_ransom_and_frees_the_captives() -> None:
    world = _armed_world()
    pending = world.progress.pending_negotiation
    card = pending.overture.card.model_copy(update={"is_confirmed_by_player": True})
    scene_id = world.progress.pending_scene_id
    price = card.terms[0].ransom_gold
    player_before = world.factions[PLAYER].treasury
    holder_before = world.factions[HOLDER].treasury

    closed, _ = close_negotiation(world, SCENARIO, scene_id, card, TermsResult.AGREED)

    assert closed.prisoners == []
    assert closed.factions[PLAYER].treasury == player_before - price
    assert closed.factions[HOLDER].treasury == holder_before + price


def _opinion_of_player(world) -> int:
    leader = world.leaders[world.factions[HOLDER].leader_id]
    return opinion_of(leader, world.factions[PLAYER].leader_id)


def test_declining_keeps_the_captives_and_costs_opinion() -> None:
    world = _armed_world()
    scene_id = world.progress.pending_scene_id
    before = _opinion_of_player(world)

    closed, _ = close_negotiation(world, SCENARIO, scene_id, None, TermsResult.REFUSED)

    assert len(closed.prisoners) == 1
    assert closed.progress.pending_scene_id is None
    assert _opinion_of_player(closed) < before


def test_negotiating_opens_a_valid_peace_scene_with_the_ransom_on_the_table() -> None:
    world = _armed_world()
    pending = world.progress.pending_negotiation

    package = _build_package(world, SCENARIO, world.progress.pending_scene_id, pending)

    assert package.scene_id == world.progress.pending_scene_id
    assert package.is_declinable is True


def test_the_card_is_unsignable_once_the_player_is_broke() -> None:
    world = _armed_world()
    card = world.progress.pending_negotiation.overture.card.model_copy(
        update={"is_confirmed_by_player": True}
    )
    world.factions[PLAYER].treasury = 0
    scene_id = world.progress.pending_scene_id

    with pytest.raises(CampaignProgressError) as error:
        close_negotiation(world, SCENARIO, scene_id, card, TermsResult.AGREED)

    assert error.value.code == "cannot_pay"


def test_legacy_peace_ruleset_makes_no_demand() -> None:
    world = make_world()
    world.peace_ruleset = 1
    _captive(world)

    assert select_overture(world, SCENARIO) is None


def test_a_haggled_lower_ransom_is_what_gets_paid() -> None:
    world = _armed_world()
    scene_id = world.progress.pending_scene_id
    card = world.progress.pending_negotiation.overture.card
    asked = card.terms[0]
    haggled_term = asked.model_copy(update={"ransom_gold": asked.ransom_gold // 2})
    haggled = card.model_copy(
        update={"terms": [haggled_term], "is_confirmed_by_player": True}
    )
    before = world.factions[PLAYER].treasury

    closed, _ = close_negotiation(
        world, SCENARIO, scene_id, haggled, TermsResult.AGREED
    )

    assert closed.prisoners == []
    assert closed.factions[PLAYER].treasury == before - asked.ransom_gold // 2


def test_ransom_demands_do_not_starve_the_npcs_other_overtures() -> None:
    from tests.engine.overtures.builders import war_world

    world = war_world(attacker_score=60)
    world.factions[PLAYER].treasury = RICH
    _captive(world, "prisoner_1")
    kinds = []
    for turn in range(40):
        world.clock.turn = turn
        world.progress.pending_scene_id = None
        world.progress.pending_negotiation = None
        arm_overture(world, SCENARIO)
        pending = world.progress.pending_negotiation
        if pending is not None:
            kinds.append(pending.overture.kind)

    assert OvertureKind.RANSOM_DEMAND in kinds
    assert OvertureKind.DEMAND in kinds
    ransom_turns = kinds.count(OvertureKind.RANSOM_DEMAND)
    assert ransom_turns < len(kinds)


def test_a_ransom_demand_waits_out_its_own_gap_before_repeating() -> None:
    world = _armed_world()
    gap = TUNING.ransom_demand_gap_turns
    world.progress.pending_scene_id = None
    world.progress.pending_negotiation = None
    world.clock.turn += gap - 1

    assert select_overture(world, SCENARIO) is None

    world.clock.turn += 1
    assert select_overture(world, SCENARIO) == (HOLDER, OvertureKind.RANSOM_DEMAND)

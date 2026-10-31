from uuid import uuid4

from app.engine.peace.signing import sign_peace
from app.engine.sieges.peace import lift_pair_sieges
from app.models.world_events import PhaseName
from app.models.world_region import OccupationState
from app.models.world_siege import SiegeState
from strategy_contracts.terms import CedeRegionTerm

from tests.engine.peace.builders import (
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_peace_card,
    make_world,
    set_score,
)

CAUTIOUS = "house_carrow"
DUNWICK_REGION = "dunwick"
CARROW_REGION = "carrow_vale"
PAIR = tuple(sorted((PLAYER, WRATHFUL_RIVAL)))


def _occupy(world, region_id: str, occupier_id: str) -> None:
    world.regions[region_id].occupation = OccupationState(
        occupier_id=occupier_id, siege_progress=100
    )


def test_lifts_occupation_between_the_pair() -> None:
    world = make_world()
    _occupy(world, DUNWICK_REGION, PLAYER)

    events = lift_pair_sieges(world, [PAIR], PhaseName.DIPLOMACY)

    assert world.regions[DUNWICK_REGION].occupation is None
    assert [event.kind for event in events] == ["occupation_lifted"]
    assert events[0].phase is PhaseName.DIPLOMACY


def test_keeps_occupation_of_a_third_party() -> None:
    world = make_world()
    _occupy(world, CARROW_REGION, WRATHFUL_RIVAL)

    events = lift_pair_sieges(world, [PAIR], PhaseName.DIPLOMACY)

    assert world.regions[CARROW_REGION].occupation is not None
    assert events == []


def test_removes_sieges_between_the_pair_only() -> None:
    world = make_world()
    world.sieges = [
        SiegeState(region_id=DUNWICK_REGION, besieger_id=PLAYER, army_ids=["a1"]),
        SiegeState(
            region_id=CARROW_REGION, besieger_id=WRATHFUL_RIVAL, army_ids=["a2"]
        ),
    ]

    lift_pair_sieges(world, [PAIR], PhaseName.DIPLOMACY)

    assert [siege.region_id for siege in world.sieges] == [CARROW_REGION]


def test_does_nothing_at_ruleset_zero() -> None:
    world = make_world()
    world.siege_ruleset = 0
    _occupy(world, DUNWICK_REGION, PLAYER)

    assert lift_pair_sieges(world, [PAIR], PhaseName.DIPLOMACY) == []
    assert world.regions[DUNWICK_REGION].occupation is not None


def test_signing_peace_clears_occupation_between_the_signers() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=40)
    _occupy(world, DUNWICK_REGION, PLAYER)
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [], tier="medium")

    events = sign_peace(world, SCENARIO, card, uuid4())

    assert world.regions[DUNWICK_REGION].occupation is None
    assert "occupation_lifted" in [event.kind for event in events]


def test_ceded_region_keeps_its_new_owner_and_loses_the_occupation() -> None:
    world = make_world()
    set_score(add_war(world), attacker=0, defender=60)
    _occupy(world, DUNWICK_REGION, PLAYER)
    cession = CedeRegionTerm(
        from_faction_id=WRATHFUL_RIVAL,
        to_faction_id=PLAYER,
        region_id=DUNWICK_REGION,
    )
    card = make_peace_card(PLAYER, WRATHFUL_RIVAL, [cession])

    sign_peace(world, SCENARIO, card, uuid4())

    assert world.regions[DUNWICK_REGION].owner_id == PLAYER
    assert world.regions[DUNWICK_REGION].occupation is None

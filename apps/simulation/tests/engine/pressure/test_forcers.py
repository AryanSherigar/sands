from app.engine.pressure.forcers import (
    expire_mediation,
    expire_subsidies,
    open_mediation,
)
from app.engine.pressure.hope import derive_hope
from app.models.world_pressure import SubsidyState
from strategy_contracts.pressure import HopeSource

from tests.engine.pressure.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

TUNING = SCENARIO.tuning.pressure


def _two_party_world():
    world = make_world()
    war = add_war(world, attacker_id=WRATHFUL_RIVAL, defender_id=PLAYER)
    return world, war


def test_mediation_requires_neutral_mediator() -> None:
    world, war = _two_party_world()

    assert open_mediation(world, SCENARIO, PLAYER, war.id) is None
    assert open_mediation(world, SCENARIO, WRATHFUL_RIVAL, war.id) is None
    offer = open_mediation(world, SCENARIO, CAUTIOUS_RIVAL, war.id)

    assert offer is not None
    assert offer.expires_turn == world.clock.turn + TUNING.mediation_ttl_turns


def test_mediation_for_unknown_war_is_refused() -> None:
    world, _ = _two_party_world()

    assert open_mediation(world, SCENARIO, CAUTIOUS_RIVAL, "war_missing") is None


def test_only_one_open_offer_per_war() -> None:
    world, war = _two_party_world()

    first = open_mediation(world, SCENARIO, CAUTIOUS_RIVAL, war.id)
    second = open_mediation(world, SCENARIO, CAUTIOUS_RIVAL, war.id)

    assert first is not None and second is None
    assert len(world.pressure.mediation_offers) == 1


def test_offer_expires_after_ttl_and_hope_ends() -> None:
    world, war = _two_party_world()
    for army in world.armies.values():
        army.morale = 0
    open_mediation(world, SCENARIO, CAUTIOUS_RIVAL, war.id)
    assert HopeSource.MEDIATION in derive_hope(world, SCENARIO, PLAYER, war).sources

    world.clock.turn += TUNING.mediation_ttl_turns + 1
    removed = expire_mediation(world)

    assert len(removed) == 1
    assert world.pressure.mediation_offers == []
    assert derive_hope(world, SCENARIO, PLAYER, war).sources == []


def test_expired_offer_allows_a_new_one() -> None:
    world, war = _two_party_world()
    open_mediation(world, SCENARIO, CAUTIOUS_RIVAL, war.id)
    world.clock.turn += TUNING.mediation_ttl_turns + 1
    expire_mediation(world)

    assert open_mediation(world, SCENARIO, CAUTIOUS_RIVAL, war.id) is not None


def test_offers_for_finished_wars_are_dropped() -> None:
    world, war = _two_party_world()
    open_mediation(world, SCENARIO, CAUTIOUS_RIVAL, war.id)
    world.wars.clear()

    assert len(expire_mediation(world)) == 1


def test_subsidies_expire() -> None:
    world, war = _two_party_world()
    world.pressure.subsidies.append(
        SubsidyState(
            id="sub_1",
            payer_id=CAUTIOUS_RIVAL,
            receiver_id=PLAYER,
            war_id=war.id,
            expires_turn=2,
        )
    )
    world.clock.turn = 3

    removed = expire_subsidies(world)

    assert [item.id for item in removed] == ["sub_1"]
    assert world.pressure.subsidies == []

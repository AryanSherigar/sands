from app.engine.ai.standing import is_bound, known_power_ratio
from app.engine.alliances.signing import sign_alliance
from app.models.world_diplomacy import (
    CommitmentState,
    CommitmentStatus,
    RelationState,
    TruceState,
)
from strategy_contracts.enums import RelationStatus, TroopType
from strategy_contracts.terms import AllianceTerm, NonAggressionTerm

from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)

SCENE_ID = "00000000-0000-0000-0000-000000000001"


def test_unrelated_factions_are_not_bound() -> None:
    assert not is_bound(make_world(), CAUTIOUS_RIVAL, WRATHFUL_RIVAL)


def test_truce_pact_and_alliance_bind_both_ways() -> None:
    truce = make_world()
    truce.truces.append(
        TruceState(faction_a=WRATHFUL_RIVAL, faction_b=CAUTIOUS_RIVAL, expires_turn=9)
    )
    pact = make_world()
    pact.commitments.append(
        CommitmentState(
            id="c1",
            term=NonAggressionTerm(
                faction_a=CAUTIOUS_RIVAL, faction_b=WRATHFUL_RIVAL, duration_turns=5
            ),
            start_turn=0,
            status=CommitmentStatus.ACTIVE,
        )
    )
    alliance = make_world()
    sign_alliance(
        alliance,
        SCENARIO,
        AllianceTerm(faction_a=CAUTIOUS_RIVAL, faction_b=WRATHFUL_RIVAL),
        SCENE_ID,
    )
    legacy = make_world()
    legacy.alliance_ruleset = 0
    low, high = sorted((CAUTIOUS_RIVAL, WRATHFUL_RIVAL))
    legacy.relations = [
        RelationState(
            faction_a=low, faction_b=high, status=RelationStatus.ALLIANCE, since_turn=0
        )
    ]

    for world in (truce, pact, alliance, legacy):
        assert is_bound(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)
        assert is_bound(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL)


def test_expired_pact_does_not_bind() -> None:
    world = make_world()
    world.commitments.append(
        CommitmentState(
            id="c1",
            term=NonAggressionTerm(
                faction_a=CAUTIOUS_RIVAL, faction_b=WRATHFUL_RIVAL, duration_turns=5
            ),
            start_turn=0,
            status=CommitmentStatus.EXPIRED,
        )
    )

    assert not is_bound(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)


def test_power_ratio_compares_own_troops_with_what_is_known() -> None:
    world = make_world()

    ratio = known_power_ratio(world, SCENARIO, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    assert ratio == 500 * 100 // 70


def test_power_ratio_is_neutral_when_nothing_is_known_of_the_target() -> None:
    world = make_world()
    world.factions[CAUTIOUS_RIVAL].intel.pop("fenwatch")

    assert known_power_ratio(world, SCENARIO, CAUTIOUS_RIVAL, WRATHFUL_RIVAL) == 100


def test_a_smaller_army_lowers_the_ratio() -> None:
    world = make_world()
    for army in world.armies.values():
        if army.owner_id == CAUTIOUS_RIVAL:
            army.troops = {TroopType.INFANTRY: 10}

    assert (
        known_power_ratio(world, SCENARIO, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)
        == 20 * 100 // 70
    )


def test_relation_status_alone_does_not_bind_an_alliance_ruleset_world() -> None:
    world = make_world()
    low, high = sorted((CAUTIOUS_RIVAL, WRATHFUL_RIVAL))
    world.relations = [
        RelationState(
            faction_a=low, faction_b=high, status=RelationStatus.ALLIANCE, since_turn=0
        )
    ]

    assert not is_bound(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

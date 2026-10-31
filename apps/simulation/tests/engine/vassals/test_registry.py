from app.engine.vassals.registry import (
    active_vassalages,
    granted_share,
    overlord_of,
    vassal_term,
    vassalage_of,
    vassals_of,
)
from app.models.world_diplomacy import CommitmentStatus
from strategy_contracts.vassal import DemandKind

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    WRATHFUL_RIVAL,
    add_vassalage,
    make_world,
)


def test_lookups_find_the_pair_from_either_side() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)

    assert vassalage_of(world, CAUTIOUS_RIVAL) is commitment
    assert vassals_of(world, PLAYER) == [commitment]
    assert active_vassalages(world, PLAYER) == [commitment]
    assert active_vassalages(world, CAUTIOUS_RIVAL) == [commitment]
    assert overlord_of(world, CAUTIOUS_RIVAL) == PLAYER
    assert overlord_of(world, PLAYER) is None
    assert vassalage_of(world, WRATHFUL_RIVAL) is None


def test_overlord_of_returns_none_after_release() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    commitment.status = CommitmentStatus.EXPIRED

    assert overlord_of(world, CAUTIOUS_RIVAL) is None


def test_expired_fixed_vassalage_is_not_in_force() -> None:
    world = make_world()
    add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, duration=2)
    world.clock.turn += 2

    assert vassalage_of(world, CAUTIOUS_RIVAL) is None


def test_granted_share_reads_the_term() -> None:
    world = make_world()
    commitment = add_vassalage(
        world, PLAYER, CAUTIOUS_RIVAL, tribute=30, levy=40, has_garrison=True
    )

    assert vassal_term(commitment).tribute_share_percent == 30
    assert granted_share(commitment, DemandKind.TRIBUTE) == 30
    assert granted_share(commitment, DemandKind.LEVY) == 40
    assert granted_share(commitment, DemandKind.GARRISON) > 0

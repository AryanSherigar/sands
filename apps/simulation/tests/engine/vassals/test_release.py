import pytest
from app.engine.vassals.commands import apply_vassal_order, validate_vassal_order
from app.engine.vassals.registry import vassalage_of
from app.exceptions.command_exceptions import CommandError
from app.models.orders import ReleaseVassalOrder
from app.models.world_diplomacy import CommitmentStatus

from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    make_demand,
    make_world,
)


def test_release_by_overlord_ends_without_breach() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    world.vassal.demands.append(make_demand(commitment))
    order = ReleaseVassalOrder(faction_id=PLAYER, vassalage_id=commitment.id)

    validate_vassal_order(world, SCENARIO, order)
    events = apply_vassal_order(world, SCENARIO, order)

    assert commitment.status is CommitmentStatus.EXPIRED
    assert vassalage_of(world, CAUTIOUS_RIVAL) is None
    assert world.oathbreakers == []
    assert world.vassal.demands == []
    assert [event.kind for event in events] == ["vassal_released"]


def test_release_by_non_overlord_is_rejected() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    order = ReleaseVassalOrder(faction_id=WRATHFUL_RIVAL, vassalage_id=commitment.id)

    with pytest.raises(CommandError) as refused:
        validate_vassal_order(world, SCENARIO, order)
    assert refused.value.code == "not_overlord"


def test_release_of_an_unknown_vassalage_is_rejected() -> None:
    order = ReleaseVassalOrder(faction_id=PLAYER, vassalage_id="commitment_9")

    with pytest.raises(CommandError) as refused:
        validate_vassal_order(make_world(), SCENARIO, order)
    assert refused.value.code == "unknown_vassalage"

import pytest
from app.engine.alliances.denounce import (
    denounce_alliance,
    expire_alliances,
    validate_denounce,
)
from app.engine.diplomacy.phase import DiplomacyPhase
from app.engine.opinion import opinion_of
from app.exceptions.command_exceptions import CommandError
from app.models.orders import DenounceAllianceOrder
from app.models.world_diplomacy import CommitmentStatus
from strategy_contracts.enums import RelationStatus

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_alliance,
    make_world,
)
from tests.engine.diplomacy.builders import queue_npc_order, run_phase

TUNING = SCENARIO.tuning.alliance
FIXED_TURNS = 5


def _relation(world, first: str, second: str) -> RelationStatus:
    pair = tuple(sorted((first, second)))
    return next(
        item.status
        for item in world.relations
        if (item.faction_a, item.faction_b) == pair
    )


def test_denounce_costs_opinion_only() -> None:
    world = make_world()
    commitment = add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    partner = world.leaders[world.factions[CAUTIOUS_RIVAL].leader_id]
    denouncer_id = world.factions[PLAYER].leader_id
    before = opinion_of(partner, denouncer_id)
    order = DenounceAllianceOrder(faction_id=PLAYER, alliance_id=commitment.id)

    events = denounce_alliance(world, SCENARIO, order)

    assert commitment.status is CommitmentStatus.EXPIRED
    assert _relation(world, PLAYER, CAUTIOUS_RIVAL) == RelationStatus.PEACE
    assert before - opinion_of(partner, denouncer_id) == TUNING.denounce_opinion_cost
    assert world.oathbreakers == []
    assert world.grounds == []
    assert [event.kind for event in events] == ["alliance_denounced"]


def test_denounce_unknown_or_ended_alliance_rejected() -> None:
    world = make_world()
    commitment = add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    commitment.status = CommitmentStatus.BREACHED

    for alliance_id in ("commitment_99", commitment.id):
        order = DenounceAllianceOrder(faction_id=PLAYER, alliance_id=alliance_id)
        with pytest.raises(CommandError) as error:
            validate_denounce(world, order)
        assert error.value.code == "unknown_alliance"


def test_denounce_by_non_member_rejected() -> None:
    world = make_world()
    commitment = add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    order = DenounceAllianceOrder(faction_id=WRATHFUL_RIVAL, alliance_id=commitment.id)

    with pytest.raises(CommandError) as error:
        validate_denounce(world, order)

    assert error.value.code == "not_member"


def test_fixed_alliance_expires_and_restores_peace() -> None:
    world = make_world()
    commitment = add_alliance(world, PLAYER, CAUTIOUS_RIVAL, duration_turns=FIXED_TURNS)
    world.clock.turn += FIXED_TURNS

    events = expire_alliances(world)

    assert commitment.status is CommitmentStatus.EXPIRED
    assert _relation(world, PLAYER, CAUTIOUS_RIVAL) == RelationStatus.PEACE
    assert [event.kind for event in events] == ["alliance_expired"]


def test_forever_alliance_never_expires() -> None:
    world = make_world()
    commitment = add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    world.clock.turn += 1000

    assert expire_alliances(world) == []
    assert commitment.status is CommitmentStatus.ACTIVE


def test_queued_denounce_lands_in_the_diplomacy_phase() -> None:
    world = make_world()
    commitment = add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    queued = queue_npc_order(
        world,
        SCENARIO,
        DenounceAllianceOrder(faction_id=PLAYER, alliance_id=commitment.id),
    )

    result = run_phase(DiplomacyPhase(), queued)

    assert result.world.commitments[0].status is CommitmentStatus.EXPIRED

import pytest
from app.engine.diplomacy.phase import DiplomacyPhase
from app.engine.vassals.registry import vassalage_of
from app.exceptions.command_exceptions import CommandError
from app.models.battle_command import CommandStatus
from app.models.orders import (
    AnnexVassalOrder,
    AnswerDemandOrder,
    DemandFromVassalOrder,
    GrantConsentOrder,
    ReleaseVassalOrder,
)
from app.models.world_diplomacy import CommitmentStatus
from strategy_contracts.vassal import ConsentAction, DemandKind, DemandReply

from tests.engine.diplomacy.builders import queue_npc_order, run_phase
from tests.engine.vassals.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_vassalage,
    make_world,
)


def _queue(world, order):
    return queue_npc_order(world, SCENARIO, order)


def test_queued_demand_is_applied_by_the_diplomacy_phase() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    queued = _queue(
        world,
        DemandFromVassalOrder(
            faction_id=PLAYER,
            vassalage_id=commitment.id,
            demand_kind=DemandKind.TRIBUTE,
            amount=70,
        ),
    )

    result = run_phase(DiplomacyPhase(), queued)

    assert [d.vassal_id for d in result.world.vassal.demands] == [CAUTIOUS_RIVAL]
    assert result.world.accepted_commands[-1].status is CommandStatus.APPLIED


def test_order_invalid_at_submission_is_rejected_with_its_code() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL, tribute=30)
    covered = DemandFromVassalOrder(
        faction_id=PLAYER,
        vassalage_id=commitment.id,
        demand_kind=DemandKind.TRIBUTE,
        amount=30,
    )
    annex = AnnexVassalOrder(faction_id=PLAYER, vassalage_id=commitment.id)

    for order, code in ((covered, "no_excess"), (annex, "score_too_low")):
        with pytest.raises(CommandError) as refused:
            _queue(world, order)
        assert refused.value.code == code


def test_order_that_goes_stale_before_the_phase_fails_and_refunds() -> None:
    world = make_world()
    commitment = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    queued = _queue(
        world,
        DemandFromVassalOrder(
            faction_id=PLAYER,
            vassalage_id=commitment.id,
            demand_kind=DemandKind.TRIBUTE,
            amount=70,
        ),
    )
    budget = queued.factions[PLAYER].orders_remaining
    next(
        c for c in queued.commitments if c.id == commitment.id
    ).status = CommitmentStatus.EXPIRED

    result = run_phase(DiplomacyPhase(), queued)

    command = result.world.accepted_commands[-1]
    assert command.status is CommandStatus.FAILED
    assert command.failure_reason == "unknown_vassalage"
    assert result.world.factions[PLAYER].orders_remaining == budget + (
        command.reserved_cost
    )


def test_queued_answer_release_and_grant_land_in_the_phase() -> None:
    world = make_world()
    commitment = add_vassalage(world, WRATHFUL_RIVAL, PLAYER, is_controlled=True)
    other = add_vassalage(world, PLAYER, CAUTIOUS_RIVAL)
    world.vassal.demands.clear()
    queued = _queue(
        world,
        ReleaseVassalOrder(faction_id=PLAYER, vassalage_id=other.id),
    )
    queued = _queue(
        queued,
        GrantConsentOrder(
            faction_id=WRATHFUL_RIVAL,
            vassalage_id=commitment.id,
            action=ConsentAction.PACT,
            target_faction_id=CAUTIOUS_RIVAL,
        ),
    )

    result = run_phase(DiplomacyPhase(), queued)

    assert vassalage_of(result.world, CAUTIOUS_RIVAL) is None
    assert len(result.world.vassal.consents) == 1


def test_queued_answer_by_the_player_vassal_resolves_the_demand() -> None:
    world = make_world()
    commitment = add_vassalage(world, WRATHFUL_RIVAL, PLAYER)
    demand_world = _queue(
        world,
        DemandFromVassalOrder(
            faction_id=WRATHFUL_RIVAL,
            vassalage_id=commitment.id,
            demand_kind=DemandKind.TRIBUTE,
            amount=60,
        ),
    )
    issued = run_phase(DiplomacyPhase(), demand_world).world
    [demand] = issued.vassal.demands
    queued = _queue(
        issued,
        AnswerDemandOrder(
            faction_id=PLAYER, demand_id=demand.id, reply=DemandReply.REFUSE
        ),
    )

    result = run_phase(DiplomacyPhase(), queued)

    assert result.world.vassal.demands == []

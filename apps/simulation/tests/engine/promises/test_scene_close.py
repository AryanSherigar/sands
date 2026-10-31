from uuid import UUID

from app.engine.negotiation import close_negotiation
from app.engine.promises.signing import sign_sworn_promise
from app.models.world_diplomacy import CommitmentStatus
from strategy_contracts.scene import TermsResult
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm, TermsCard

from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_alliance_term,
    make_world,
)

SCENE_ID = UUID("66666666-6666-6666-6666-666666666666")


def _confirmed(term) -> TermsCard:
    return TermsCard(
        proposer_id=PLAYER,
        counterpart_id=CAUTIOUS_RIVAL,
        terms=[term],
        is_confirmed_by_player=True,
        is_confirmed_by_counterpart=True,
    )


def test_alliance_signed_in_a_scene_breaks_never_ally_with() -> None:
    world = make_world()
    sign_sworn_promise(
        world,
        SwornPromiseTerm(
            promisor_id=PLAYER,
            beneficiary_id=WRATHFUL_RIVAL,
            promise=PromiseKind.NEVER_ALLY_WITH,
            subject_id=CAUTIOUS_RIVAL,
            duration_turns=9,
        ),
        None,
    )
    world.progress.pending_scene_id = SCENE_ID
    card = _confirmed(make_alliance_term(PLAYER, CAUTIOUS_RIVAL))

    closed, events = close_negotiation(
        world, SCENARIO, SCENE_ID, card, TermsResult.AGREED
    )

    promise = next(item for item in closed.commitments if item.id == "commitment_1")
    assert promise.status is CommitmentStatus.BREACHED
    assert "sworn_promise_broken" in [event.kind for event in events]
    assert [mark.faction_id for mark in closed.oathbreakers] == [PLAYER]

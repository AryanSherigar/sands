import pytest
from app.engine import negotiation
from app.engine.hashing import world_hash
from app.engine.replay import replay_history
from app.exceptions.world_exceptions import ReplayMismatchError
from app.models.battle_progress import OperationGuard
from app.models.replay import (
    BeginNegotiationReplayInput,
    ReplayStep,
    ResolveNegotiationReplayInput,
)
from strategy_contracts.examples import load_three_crowns
from strategy_contracts.terms import NonAggressionTerm, TermsCard

from tests.engine.test_negotiation import PLAYER, RIVAL, _world
from tests.models.builders import PLAYTHROUGH_ID

SCENARIO = load_three_crowns()
GUARD = OperationGuard(
    operation_id="op-1", expected_world_version=1, expected_turn=4, expected_wave=0
)
CARD = TermsCard(
    proposer_id=PLAYER,
    counterpart_id=RIVAL,
    terms=[NonAggressionTerm(faction_a=PLAYER, faction_b=RIVAL, duration_turns=6)],
    is_confirmed_by_player=True,
    is_confirmed_by_counterpart=True,
)


def _steps(after_resolve: str | None = None):
    start = _world(["pragmatic"])
    opened = negotiation.open_negotiation(start, RIVAL, GUARD.operation_id)
    scene_id = opened.progress.pending_scene_id
    closed, _ = negotiation.close_negotiation(opened, SCENARIO, scene_id, CARD)
    steps = [
        ReplayStep(
            playthrough_id=PLAYTHROUGH_ID,
            sequence=1,
            operation_id="op-1",
            kind="begin_negotiation",
            input=BeginNegotiationReplayInput(
                guard=GUARD, counterpart_faction_id=RIVAL
            ),
            before_hash=world_hash(start),
            after_hash=world_hash(opened),
            turn=4,
            wave=0,
        ),
        ReplayStep(
            playthrough_id=PLAYTHROUGH_ID,
            sequence=2,
            operation_id="op-2",
            kind="resolve_negotiation",
            input=ResolveNegotiationReplayInput(
                guard=GUARD, scene_id=scene_id, terms_card=CARD
            ),
            before_hash=world_hash(opened),
            after_hash=after_resolve or world_hash(closed),
            turn=4,
            wave=0,
        ),
    ]
    return start, steps, closed


def test_negotiation_steps_replay_to_the_live_world_hash() -> None:
    start, steps, closed = _steps()
    result = replay_history(start, SCENARIO, steps)
    assert result.world_hash == world_hash(closed)
    assert result.world.commitments == closed.commitments


def test_a_tampered_card_is_caught_at_the_resolving_step() -> None:
    start, steps, _ = _steps()
    other = CARD.model_copy(
        update={
            "terms": [
                NonAggressionTerm(faction_a=PLAYER, faction_b=RIVAL, duration_turns=9)
            ]
        }
    )
    steps[1] = steps[1].model_copy(
        update={"input": steps[1].input.model_copy(update={"terms_card": other})}
    )
    with pytest.raises(ReplayMismatchError):
        replay_history(start, SCENARIO, steps)

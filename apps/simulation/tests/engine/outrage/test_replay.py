from uuid import UUID

from app.engine.diplomacy.phase import TimePhase
from app.engine.hashing import world_hash
from app.engine.negotiation import close_negotiation
from app.engine.outrage.status import outrage_of
from app.models.world_state import WorldState
from strategy_contracts.scene import RefusedDemand, TermsResult
from strategy_contracts.terms import PayGoldTerm, TermsCard

from tests.engine.diplomacy.builders import run_phase
from tests.engine.outrage.builders import PLAYER, SCENARIO, WRATHFUL_RIVAL, make_world

SCENE_ID = UUID("00000000-0000-0000-0000-000000000009")
TURNS = 15
TONE = 5
HUGE_DEMAND = 10_000


def _refused_scene() -> WorldState:
    world = make_world()
    world.progress.pending_scene_id = SCENE_ID
    world.progress.negotiation_counterpart_id = WRATHFUL_RIVAL
    card = TermsCard(
        proposer_id=PLAYER,
        counterpart_id=WRATHFUL_RIVAL,
        terms=[
            PayGoldTerm(payer_id=WRATHFUL_RIVAL, payee_id=PLAYER, amount=HUGE_DEMAND)
        ],
    )
    refused = RefusedDemand(terms_card=card, tone_grade=TONE)
    return close_negotiation(
        world, SCENARIO, SCENE_ID, None, TermsResult.REFUSED, refused
    )[0]


def _play() -> tuple[list[str], WorldState]:
    world = _refused_scene()
    hashes = [world_hash(world)]
    for _ in range(TURNS):
        world.clock.turn += 1
        world = run_phase(TimePhase(), world).world
        hashes.append(world_hash(world))
    return hashes, world


def test_a_demand_refusal_and_fade_replay_to_identical_hashes() -> None:
    first, _ = _play()
    second, _ = _play()

    assert first == second


def test_outrage_changes_the_world_hash_and_then_fades_away() -> None:
    hashes, final = _play()

    assert hashes[0] != world_hash(make_world())
    assert outrage_of(final, WRATHFUL_RIVAL) is None


def test_outrage_state_survives_a_document_round_trip() -> None:
    world = _refused_scene()

    restored = WorldState.model_validate(world.model_dump(mode="json"))

    assert world_hash(restored) == world_hash(world)
    assert restored.outrage == world.outrage

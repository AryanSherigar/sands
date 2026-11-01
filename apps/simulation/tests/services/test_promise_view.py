from app.engine.promises.signing import sign_sworn_promise
from app.models.world_diplomacy import CommitmentStatus
from app.services.world_projection import project_world
from strategy_contracts.terms import PromiseKind, SwornPromiseTerm
from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)


def _view(world):
    return project_world(world, SCENARIO, 1, "digest").model_dump(mode="json")


def _swear(world, promisor: str, beneficiary: str, **extra) -> None:
    term = SwornPromiseTerm(
        promisor_id=promisor,
        beneficiary_id=beneficiary,
        promise=extra.pop("promise", PromiseKind.NEVER_ATTACK_FACTION),
        duration_turns=5,
        **extra,
    )
    sign_sworn_promise(world, term, None)


def test_projection_lists_active_promises_involving_the_player() -> None:
    world = make_world()
    world.clock.turn = 3
    _swear(world, PLAYER, WRATHFUL_RIVAL)
    _swear(world, CAUTIOUS_RIVAL, PLAYER, promise=PromiseKind.SPARE_PRISONERS)

    promises = _view(world)["sworn_promises"]

    assert [(item["promisor_id"], item["beneficiary_id"]) for item in promises] == [
        (PLAYER, WRATHFUL_RIVAL),
        (CAUTIOUS_RIVAL, PLAYER),
    ]
    assert promises[0] == {
        "commitment_id": "commitment_1",
        "promisor_id": PLAYER,
        "beneficiary_id": WRATHFUL_RIVAL,
        "promise": "never_attack_faction",
        "subject_id": None,
        "end_turn": 8,
    }


def test_projection_hides_promises_between_other_factions() -> None:
    world = make_world()
    _swear(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    assert _view(world)["sworn_promises"] == []


def test_projection_omits_breached_promises() -> None:
    world = make_world()
    _swear(world, PLAYER, WRATHFUL_RIVAL)
    world.commitments[0].status = CommitmentStatus.BREACHED

    assert _view(world)["sworn_promises"] == []

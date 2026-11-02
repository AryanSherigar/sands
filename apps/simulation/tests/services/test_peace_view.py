from app.engine.peace.hostages import hold_hostage
from app.models.world_diplomacy import TruceState
from app.models.world_pressure import MediationOffer
from app.services.world_projection import project_world
from strategy_contracts.peace import PeaceTier
from strategy_contracts.terms import HostageTerm
from tests.engine.peace.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_war,
    make_world,
)

FORBIDDEN_KEYS = {
    "breach",
    "pressure",
    "harshness",
    "loser_id",
    "accept_at",
    "haggle_at",
    "lapses",
    "ransom_points",
}


def _view(world):
    return project_world(world, SCENARIO, 1, "digest")


def _keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()


def _truce(a: str, b: str, truce_id: str, tier=PeaceTier.MEDIUM) -> TruceState:
    first, second = sorted((a, b))
    return TruceState(
        id=truce_id,
        faction_a=first,
        faction_b=second,
        expires_turn=40,
        tier=tier,
        loser_id=first,
        harshness=77,
    )


def test_view_lists_own_truces_only() -> None:
    world = make_world()
    world.truces = [
        _truce(PLAYER, WRATHFUL_RIVAL, "truce_1"),
        _truce(CAUTIOUS_RIVAL, WRATHFUL_RIVAL, "truce_2"),
    ]

    truces = _view(world).model_dump(mode="json")["truces"]

    assert [(t["faction_a"], t["faction_b"]) for t in truces] == [
        tuple(sorted((PLAYER, WRATHFUL_RIVAL)))
    ]
    assert truces[0]["tier"] == "medium"


def test_perpetual_truce_has_no_expiry_in_the_view() -> None:
    world = make_world()
    truce = _truce(PLAYER, WRATHFUL_RIVAL, "truce_1", PeaceTier.PERPETUAL)
    truce.expires_turn = 0
    world.truces = [truce]

    truces = _view(world).model_dump(mode="json")["truces"]

    assert truces[0]["expires_turn"] is None


def test_view_lists_own_hostages() -> None:
    world = make_world()
    truce = _truce(PLAYER, WRATHFUL_RIVAL, "truce_1")
    world.truces = [truce]
    term = HostageTerm(
        giver_id=WRATHFUL_RIVAL,
        holder_id=PLAYER,
        leader_id=world.factions[WRATHFUL_RIVAL].leader_id,
        duration_turns=5,
    )
    hold_hostage(world, term, truce.id)

    hostages = _view(world).model_dump(mode="json")["own_hostages"]

    assert hostages[0]["holder_id"] == PLAYER


def test_view_lists_open_mediation_for_the_players_war() -> None:
    world = make_world()
    war = add_war(world)
    world.pressure.mediation_offers.append(
        MediationOffer(
            id="mediation_1",
            mediator_id=CAUTIOUS_RIVAL,
            war_id=war.id,
            expires_turn=world.clock.turn + 3,
        )
    )

    offers = _view(world).model_dump(mode="json")["open_mediations"]

    assert offers == [
        {
            "id": "mediation_1",
            "mediator_id": CAUTIOUS_RIVAL,
            "war_id": war.id,
            "expires_turn": world.clock.turn + 3,
        }
    ]


def test_view_lists_the_players_wars_with_their_participants() -> None:
    world = make_world()
    war = add_war(world)
    add_war(
        world, attacker_id=CAUTIOUS_RIVAL, defender_id=WRATHFUL_RIVAL, war_id="war_2"
    )

    wars = _view(world).model_dump(mode="json")["wars"]

    assert wars == [
        {
            "id": war.id,
            "attacker_id": WRATHFUL_RIVAL,
            "defender_id": PLAYER,
            "participant_ids": [WRATHFUL_RIVAL, PLAYER],
            "outlook": "even",
            "goal_slots": 1,
        }
    ]


def test_view_never_contains_breach_pressure_or_acceptance_numbers() -> None:
    world = make_world()
    world.truces = [_truce(PLAYER, WRATHFUL_RIVAL, "truce_1")]

    keys = _keys(_view(world).model_dump(mode="json"))

    assert not keys & FORBIDDEN_KEYS

from app.engine.diplomacy.war_declaration import declare_war
from app.models.orders import DeclareWarOrder
from app.services.world_projection import project_world
from strategy_contracts.alliance import AllianceType
from tests.engine.alliances.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    add_alliance,
    make_world,
)

FORBIDDEN_KEYS = {
    "standing",
    "refusals_by_faction",
    "join_score",
    "temperament",
    "strength",
    "legitimacy",
}
FIXED_TURNS = 7


def _view(world):
    return project_world(world, SCENARIO, 1, "digest").model_dump(mode="json")


def _keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()


def test_view_lists_player_alliances_only() -> None:
    world = make_world()
    add_alliance(
        world,
        PLAYER,
        CAUTIOUS_RIVAL,
        AllianceType.OFFENSIVE,
        duration_turns=FIXED_TURNS,
        is_separate_peace_banned=True,
    )
    add_alliance(world, CAUTIOUS_RIVAL, WRATHFUL_RIVAL)

    alliances = _view(world)["alliances"]

    assert alliances == [
        {
            "id": "commitment_1",
            "partner_id": CAUTIOUS_RIVAL,
            "alliance_type": "offensive",
            "ends_turn": world.clock.turn + FIXED_TURNS,
            "is_separate_peace_banned": True,
        }
    ]


def test_forever_alliance_has_no_end_turn_in_the_view() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)

    assert _view(world)["alliances"][0]["ends_turn"] is None


def test_view_lists_calls_addressed_to_the_player_only() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    add_alliance(world, WRATHFUL_RIVAL, CAUTIOUS_RIVAL, AllianceType.OFFENSIVE)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=CAUTIOUS_RIVAL),
    )

    calls = _view(world)["pending_calls"]

    assert [
        (call["caller_id"], call["side"], call["is_defensive"]) for call in calls
    ] == [(CAUTIOUS_RIVAL, "defender", True)]
    assert calls[0]["deadline_turn"] == world.alliance.calls[0].deadline_turn


def test_view_hides_npc_join_scores_and_standing() -> None:
    world = make_world()
    add_alliance(world, PLAYER, CAUTIOUS_RIVAL)
    declare_war(
        world,
        SCENARIO,
        DeclareWarOrder(faction_id=WRATHFUL_RIVAL, target_faction_id=PLAYER),
    )

    assert not _keys(_view(world)) & FORBIDDEN_KEYS

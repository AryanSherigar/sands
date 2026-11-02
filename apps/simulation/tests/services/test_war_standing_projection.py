from app.engine.diplomacy.grounds import grant_ground
from app.models.world_diplomacy import WarState
from app.services.world_projection import project_world
from strategy_contracts.diplomacy import GroundKind
from tests.engine.diplomacy.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    WRATHFUL_RIVAL,
    make_world,
)


def _view(world):
    return project_world(world, SCENARIO, 1, "digest").model_dump(mode="json")


def _war(world, attacker_score: int, defender_score: int, attacker: str = PLAYER):
    defender = WRATHFUL_RIVAL if attacker == PLAYER else PLAYER
    world.wars.append(
        WarState(
            id="war_1",
            attacker_id=attacker,
            defender_id=defender,
            participant_ids=[attacker, defender],
            started_turn=0,
            war_score_attacker=attacker_score,
            war_score_defender=defender_score,
        )
    )


def test_war_view_reports_standing_bands_never_scores() -> None:
    world = make_world()
    _war(world, 60, 20)

    war = _view(world)["wars"][0]

    assert war["outlook"] == "leading"
    assert "war_score_attacker" not in war and "war_score_defender" not in war


def test_war_view_standing_follows_the_players_side() -> None:
    world = make_world()
    _war(world, 60, 20, attacker=WRATHFUL_RIVAL)

    assert _view(world)["wars"][0]["outlook"] == "trailing"


def test_close_scores_read_even_and_goal_slots_grow_with_score() -> None:
    world = make_world()
    _war(world, 25, 22)
    view = _view(world)["wars"][0]
    assert view["outlook"] == "even"
    assert view["goal_slots"] == 1

    world.wars[0].war_score_attacker = 80
    assert _view(world)["wars"][0]["goal_slots"] > 1


def test_usable_grounds_lists_only_the_players_own_usable_grounds() -> None:
    world = make_world()
    own = grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.CLAIM,
        holder_faction_id=PLAYER,
        target_faction_id=CAUTIOUS_RIVAL,
        region_id="brennmoor",
    )
    grant_ground(
        world,
        SCENARIO,
        kind=GroundKind.CLAIM,
        holder_faction_id=WRATHFUL_RIVAL,
        target_faction_id=PLAYER,
        region_id="brennmoor",
    )

    grounds = _view(world)["usable_grounds"]

    assert [item["id"] for item in grounds] == [own.id]
    assert set(grounds[0]) == {"id", "kind", "target_faction_id", "region_id"}

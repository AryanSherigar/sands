from app.engine.coalitions.phase import tick_coalitions
from app.services.world_projection import project_world
from tests.engine.coalitions.builders import (
    CAUTIOUS_RIVAL,
    PLAYER,
    SCENARIO,
    make_threat_world,
)

FORBIDDEN_KEYS = {"join_threat", "threshold", "atrocities", "conquests"}


def _view(world):
    return project_world(world, SCENARIO, 1, "digest")


def _formed_world():
    world = make_threat_world()
    world.coalition.atrocities[PLAYER] = 60
    tick_coalitions(world, SCENARIO)
    return world


def test_target_and_members_see_the_coalition_clearly() -> None:
    world = _formed_world()

    view = _view(world)

    assert [item.target_id for item in view.coalitions] == [PLAYER]
    assert CAUTIOUS_RIVAL in view.coalitions[0].member_ids


def test_own_threat_shows_a_band_and_named_factors() -> None:
    view = _view(_formed_world())

    assert view.own_threat is not None
    assert set(view.own_threat.factors) == {
        "conquest",
        "treaty_breaking",
        "atrocity",
        "balance",
    }


def test_view_never_carries_hidden_tuning_or_ledger_keys() -> None:
    dumped = _view(_formed_world()).model_dump(mode="json")

    assert FORBIDDEN_KEYS.isdisjoint(_keys(dumped))


def test_a_legacy_world_has_no_threat_and_no_coalitions() -> None:
    world = _formed_world()
    world.coalition_ruleset = 0

    view = _view(world)

    assert view.own_threat is None
    assert view.coalitions == []


def _keys(node: object) -> set[str]:
    if isinstance(node, dict):
        return set(node) | {k for v in node.values() for k in _keys(v)}
    if isinstance(node, list):
        return {k for v in node for k in _keys(v)}
    return set()

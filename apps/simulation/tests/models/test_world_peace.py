from app.engine.hashing import canonical_world_json
from app.engine.ordering import canonicalize_lists
from app.models.world_diplomacy import TruceState
from app.models.world_peace import BreachPressureState, HostageState, PeaceState
from app.models.world_state import CURRENT_PEACE_RULESET
from strategy_contracts.peace import PeaceTier

from tests.models.builders import make_world


def test_legacy_world_serializes_without_peace_keys() -> None:
    text = canonical_world_json(make_world())

    assert "peace_ruleset" not in text
    assert '"peace"' not in text


def test_ruleset_one_world_carries_peace_fields() -> None:
    world = make_world()
    world.peace_ruleset = CURRENT_PEACE_RULESET

    text = canonical_world_json(world)

    assert f'"peace_ruleset":{CURRENT_PEACE_RULESET}' in text
    assert '"peace":{' in text


def test_peace_state_defaults_are_empty() -> None:
    state = PeaceState()

    assert state.hostages == []
    assert state.breach == []
    assert state.lapses == []
    assert state.ransom_points == {}


def test_truce_defaults_describe_a_plain_legacy_truce() -> None:
    truce = TruceState(faction_a="aa", faction_b="bb", expires_turn=10)

    assert truce.tier is None
    assert truce.guarantor_ids == []
    assert truce.is_fragile is False
    assert truce.origin_war_id is None


def test_peace_lists_are_sorted_by_canonicalize_lists() -> None:
    world = make_world()
    world.peace.hostages = [
        HostageState(
            id="hostage_2",
            giver_id="aa",
            holder_id="bb",
            leader_id="lead_a",
            release_turn=9,
            truce_id="truce_1",
        ),
        HostageState(
            id="hostage_1",
            giver_id="aa",
            holder_id="bb",
            leader_id="lead_b",
            release_turn=9,
            truce_id="truce_1",
        ),
    ]
    world.peace.breach = [
        BreachPressureState(faction_a="cc", faction_b="dd", pressure=3),
        BreachPressureState(faction_a="aa", faction_b="bb", pressure=3),
    ]
    world.truces = [
        TruceState(id="truce_2", faction_a="cc", faction_b="dd", tier=PeaceTier.SHORT),
        TruceState(id="truce_1", faction_a="aa", faction_b="bb", tier=PeaceTier.SHORT),
    ]

    canonicalize_lists(world)

    assert [item.id for item in world.peace.hostages] == ["hostage_1", "hostage_2"]
    assert [item.faction_a for item in world.peace.breach] == ["aa", "cc"]
    assert [item.id for item in world.truces] == ["truce_1", "truce_2"]

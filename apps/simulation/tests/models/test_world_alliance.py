from app.engine.hashing import canonical_world_json
from app.engine.ordering import canonicalize_lists
from app.models.world_alliance import (
    AllianceStanding,
    AllianceWorldState,
    CallToArmsState,
)
from app.models.world_diplomacy import WarSide, WarState
from app.models.world_state import CURRENT_ALLIANCE_RULESET

from tests.models.builders import make_world


def _call(call_id: str) -> CallToArmsState:
    return CallToArmsState(
        id=call_id,
        alliance_id="commitment_1",
        war_id="war_1",
        caller_id="aa",
        ally_id="cc",
        side=WarSide.ATTACKER,
        issued_turn=3,
        deadline_turn=4,
        is_defensive=False,
    )


def test_legacy_world_serializes_without_alliance_keys() -> None:
    text = canonical_world_json(make_world())

    assert "alliance_ruleset" not in text
    assert '"alliance"' not in text


def test_ruleset_one_world_carries_alliance_fields() -> None:
    world = make_world()
    world.alliance_ruleset = CURRENT_ALLIANCE_RULESET

    text = canonical_world_json(world)

    assert '"alliance_ruleset":1' in text
    assert '"alliance":{' in text


def test_war_without_side_map_hashes_as_before() -> None:
    world = make_world()
    world.wars.append(
        WarState(id="war_1", attacker_id="aa", defender_id="bb", started_turn=1)
    )

    assert "side_by_faction" not in canonical_world_json(world)


def test_war_with_side_map_serializes_it() -> None:
    world = make_world()
    world.wars.append(
        WarState(
            id="war_1",
            attacker_id="aa",
            defender_id="bb",
            started_turn=1,
            side_by_faction={"aa": WarSide.ATTACKER, "bb": WarSide.DEFENDER},
        )
    )

    assert '"side_by_faction":{"aa":"attacker","bb":"defender"}' in (
        canonical_world_json(world)
    )


def test_alliance_state_defaults_are_empty() -> None:
    state = AllianceWorldState()

    assert state.calls == []
    assert state.standing == []


def test_calls_and_standing_sorted_by_canonicalize_lists() -> None:
    world = make_world()
    world.alliance.calls = [_call("call_2"), _call("call_1")]
    world.alliance.standing = [
        AllianceStanding(alliance_id="commitment_2"),
        AllianceStanding(alliance_id="commitment_1"),
    ]

    canonicalize_lists(world)

    assert [call.id for call in world.alliance.calls] == ["call_1", "call_2"]
    assert [item.alliance_id for item in world.alliance.standing] == [
        "commitment_1",
        "commitment_2",
    ]

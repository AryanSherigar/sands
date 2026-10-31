from app.engine.hashing import canonical_world_json, world_hash
from app.models.world_diplomacy import EnvoyState
from app.models.world_state import WorldState

from tests.models.builders import make_world

HASH_LENGTH = 64


def test_same_world_gives_the_same_hash() -> None:
    assert world_hash(make_world()) == world_hash(make_world())


def test_hash_is_hex_sha256() -> None:
    digest = world_hash(make_world())
    assert len(digest) == HASH_LENGTH
    int(digest, 16)


def test_changing_one_number_changes_the_hash() -> None:
    world = make_world()
    changed = world.model_copy(deep=True)
    changed.regions["ashford"].unrest = 11
    assert world_hash(changed) != world_hash(world)


def test_dict_insertion_order_does_not_change_the_hash() -> None:
    world = make_world()
    reordered = WorldState.model_validate(
        {
            **world.model_dump(),
            "regions": dict(reversed(list(world.model_dump()["regions"].items()))),
        }
    )
    assert list(reordered.regions) != list(world.regions)
    assert world_hash(reordered) == world_hash(world)


def test_canonical_json_has_no_whitespace_outside_strings() -> None:
    text = canonical_world_json(make_world())
    assert ", " not in text
    assert ": " not in text


def test_an_epithet_changes_the_hash_but_an_absent_one_does_not_appear() -> None:
    world = make_world()
    plain = world_hash(world)
    assert "epithet" not in canonical_world_json(world)
    world.ruler.epithet = "The Unbowed"
    assert world_hash(world) != plain


def test_legacy_world_omits_diplomacy_fields() -> None:
    text = canonical_world_json(make_world())

    assert "diplomacy_ruleset" not in text
    assert '"grounds"' not in text


def test_ruleset_one_world_carries_diplomacy_fields() -> None:
    world = make_world()
    world.diplomacy_ruleset = 1

    text = canonical_world_json(world)

    assert '"diplomacy_ruleset":1' in text
    assert '"grounds":[]' in text


def test_legacy_world_omits_ai_ruleset() -> None:
    assert "ai_ruleset" not in canonical_world_json(make_world())


def test_ruleset_one_world_carries_ai_ruleset() -> None:
    world = make_world()
    world.ai_ruleset = 1

    assert '"ai_ruleset":1' in canonical_world_json(world)


def test_world_below_ruleset_two_omits_aims() -> None:
    world = make_world()
    world.ai_ruleset = 1

    assert '"aims"' not in canonical_world_json(world)


def test_ruleset_two_world_carries_aims() -> None:
    world = make_world()
    world.ai_ruleset = 2

    assert '"aims":{}' in canonical_world_json(world)


def test_legacy_world_omits_endings_fields() -> None:
    text = canonical_world_json(make_world())

    assert "endings_ruleset" not in text
    assert "stability_collapse_turns" not in text


def test_endings_ruleset_world_carries_endings_fields() -> None:
    world = make_world()
    world.endings_ruleset = 1

    text = canonical_world_json(world)

    assert '"endings_ruleset":1' in text
    assert '"stability_collapse_turns":0' in text


def test_agentless_envoy_serialises_without_an_agent_key() -> None:
    envoy = EnvoyState(id="envoy_1", from_faction_id="house_a", at_faction_id="house_b")

    assert "agent" not in envoy.model_dump(mode="json")


def test_legacy_world_omits_treaty_ruleset() -> None:
    assert "treaty_ruleset" not in canonical_world_json(make_world())


def test_treaty_ruleset_one_world_carries_the_flag() -> None:
    world = make_world()
    world.treaty_ruleset = 1

    assert '"treaty_ruleset":1' in canonical_world_json(world)

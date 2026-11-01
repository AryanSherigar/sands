from app.engine.hashing import canonical_world_json
from app.models.world_state import CURRENT_COALITION_RULESET

from tests.models.builders import make_world


def test_current_ruleset_is_one() -> None:
    assert CURRENT_COALITION_RULESET == 1


def test_legacy_world_dump_has_no_coalition_keys() -> None:
    text = canonical_world_json(make_world())

    assert "coalition_ruleset" not in text
    assert '"coalition"' not in text


def test_ruleset_one_world_carries_coalition_fields() -> None:
    world = make_world()
    world.coalition_ruleset = CURRENT_COALITION_RULESET

    text = canonical_world_json(world)

    assert '"coalition_ruleset":1' in text
    assert '"coalition":{' in text

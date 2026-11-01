from app.engine.hashing import canonical_world_json
from app.models.world_diplomacy import OutrageState
from app.models.world_state import CURRENT_OUTRAGE_RULESET
from strategy_contracts.scene import OutrageLevel

from tests.models.builders import make_world


def test_current_ruleset_is_two() -> None:
    assert CURRENT_OUTRAGE_RULESET == 2


def test_legacy_world_dump_has_no_outrage_ruleset_key() -> None:
    text = canonical_world_json(make_world())

    assert "outrage_ruleset" not in text
    assert '"outrage":[]' in text


def test_current_ruleset_world_carries_the_ruleset_key() -> None:
    world = make_world()
    world.outrage_ruleset = CURRENT_OUTRAGE_RULESET

    assert '"outrage_ruleset":2' in canonical_world_json(world)


def test_outrage_state_records_target_and_mobilization() -> None:
    state = OutrageState(
        faction_id="f2",
        level=OutrageLevel.ENRAGED,
        expires_turn=6,
        target_faction_id="f1",
        mobilized_until_turn=8,
    )

    assert state.target_faction_id == "f1"
    assert state.mobilized_until_turn == 8

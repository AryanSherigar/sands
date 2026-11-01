from app.engine.hashing import canonical_world_json
from app.engine.ordering import canonicalize_lists
from app.models.world_state import CURRENT_SUCCESSION_RULESET
from app.models.world_succession import CrisisState, SuccessionWorldState

from tests.models.builders import make_world


def _crisis(faction_id: str) -> CrisisState:
    return CrisisState(
        faction_id=faction_id,
        ends_turn=9,
        regent_id=f"regent_{faction_id}",
        heir_id=None,
        heir_comes_of_age_turn=None,
        is_penalty_active=True,
    )


def test_ruleset_zero_world_omits_succession_keys_from_dump() -> None:
    text = canonical_world_json(make_world())

    assert "succession_ruleset" not in text
    assert '"succession"' not in text


def test_current_ruleset_world_carries_succession_fields() -> None:
    world = make_world()
    world.succession_ruleset = CURRENT_SUCCESSION_RULESET

    text = canonical_world_json(world)

    assert '"succession_ruleset":2' in text
    assert '"succession":{' in text


def test_succession_state_defaults_are_empty() -> None:
    assert SuccessionWorldState().crises == []


def test_crises_are_sorted_by_faction_id() -> None:
    world = make_world()
    world.succession.crises = [_crisis("bb"), _crisis("aa")]

    canonicalize_lists(world)

    assert [crisis.faction_id for crisis in world.succession.crises] == ["aa", "bb"]

from app.engine.hashing import canonical_world_json
from app.models.world_events import EndingState
from app.models.world_state import CURRENT_ENDINGS_RULESET
from strategy_contracts.endings import EndingGrade
from strategy_contracts.scenario import EndingKind

from tests.models.builders import make_world


def test_current_ruleset_is_two() -> None:
    assert CURRENT_ENDINGS_RULESET == 2


def test_ruleset_one_world_omits_endings_key() -> None:
    world = make_world()
    world.endings_ruleset = 1

    assert '"endings":' not in canonical_world_json(world)


def test_ruleset_two_world_serialises_endings_counters() -> None:
    world = make_world()
    world.endings_ruleset = 2

    text = canonical_world_json(world)

    assert '"regime_fall_turns":0' in text
    assert '"has_seen_war":false' in text


def test_ending_state_without_grade_serialises_as_before() -> None:
    ending = EndingState(
        ending_id="default_defeat_revolution", kind=EndingKind.DEFEAT, turn=3
    )

    assert ending.model_dump(mode="json") == {
        "ending_id": "default_defeat_revolution",
        "kind": "defeat",
        "turn": 3,
    }


def test_graded_ending_state_carries_grade_and_inputs() -> None:
    ending = EndingState(
        ending_id="default_defeat_revolution",
        kind=EndingKind.GRADED,
        turn=3,
        grade=EndingGrade.PYRRHIC,
        inputs={"position": 60},
    )

    dumped = ending.model_dump(mode="json")

    assert dumped["grade"] == "pyrrhic"
    assert dumped["inputs"] == {"position": 60}

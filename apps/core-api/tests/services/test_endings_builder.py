import json
import uuid
from datetime import UTC, datetime

from app.repositories.endings_repo import EndedRunRow, SnapshotEndingsRow
from app.services.endings_builder import build_scenario_endings

SCENARIO = uuid.uuid4()
NOW = datetime(2026, 10, 26, tzinfo=UTC)
ID_A, ID_B, ID_SECRET = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()


def cond(title, tag="win", is_secret=False, cid=None, priority=0):
    entry = {
        "outcome_title": title,
        "outcome_tag": tag,
        "is_secret": is_secret,
        "priority": priority,
    }
    if cid:
        entry["end_condition_id"] = str(cid)
    return entry


def snap(*conditions):
    return SnapshotEndingsRow(SCENARIO, "The Cairn", NOW, list(conditions))


def run(title, tag="win", outcome_id=None, scenario_id=SCENARIO):
    return EndedRunRow(scenario_id, outcome_id, title, tag)


def test_no_conditions_and_no_endings_yields_none() -> None:
    assert build_scenario_endings(snap(), []) is None


def test_unfound_slots_are_locked_and_never_carry_names() -> None:
    result = build_scenario_endings(
        snap(cond("Ashen", cid=ID_A), cond("Consumed", "lose", cid=ID_B)), []
    )
    assert result is not None
    assert (result.found_count, result.total_count) == (0, 2)
    assert [(s.is_found, s.title, s.outcome_tag) for s in result.slots] == [
        (False, None, None),
        (False, None, None),
    ]
    assert "Ashen" not in json.dumps(result.model_dump(mode="json"))


def test_unfound_secret_is_excluded_from_total_and_output() -> None:
    result = build_scenario_endings(
        snap(
            cond("Ashen", cid=ID_A),
            cond("The Vigil", is_secret=True, cid=ID_SECRET),
        ),
        [],
    )
    assert result is not None
    assert result.total_count == 1
    assert "Vigil" not in json.dumps(result.model_dump(mode="json"))


def test_found_secret_is_shown_and_counted() -> None:
    result = build_scenario_endings(
        snap(
            cond("Ashen", cid=ID_A),
            cond("The Vigil", is_secret=True, cid=ID_SECRET),
        ),
        [run("The Vigil", outcome_id=ID_SECRET)],
    )
    assert result is not None
    assert (result.found_count, result.total_count) == (1, 2)
    assert [s.title for s in result.slots if s.is_found] == ["The Vigil"]


def test_id_match_beats_title_and_duplicate_runs_count_once() -> None:
    result = build_scenario_endings(
        snap(cond("Ashen", cid=ID_A)),
        [run("Ashen", outcome_id=ID_A), run("Ashen", outcome_id=ID_A)],
    )
    assert result is not None
    assert (result.found_count, result.total_count) == (1, 1)


def test_legacy_run_matches_by_title() -> None:
    result = build_scenario_endings(snap(cond("Ashen", cid=ID_A)), [run("Ashen")])
    assert result is not None
    assert (result.found_count, result.total_count) == (1, 1)
    assert result.slots[0].title == "Ashen"
    assert result.slots[0].outcome_tag == "win"


def test_renamed_or_removed_ending_still_counts_as_an_extra_found_slot() -> None:
    result = build_scenario_endings(
        snap(cond("Ashen v2", cid=ID_A)),
        [run("Old Name", tag="lose", outcome_id=uuid.uuid4())],
    )
    assert result is not None
    assert (result.found_count, result.total_count) == (1, 2)
    found = [s for s in result.slots if s.is_found]
    assert (found[0].title, found[0].outcome_tag) == ("Old Name", "lose")


def test_story_with_only_removed_endings_is_still_reported() -> None:
    result = build_scenario_endings(snap(), [run("Gone", outcome_id=uuid.uuid4())])
    assert result is not None
    assert (result.found_count, result.total_count) == (1, 1)


def test_slots_follow_priority_order() -> None:
    result = build_scenario_endings(
        snap(cond("Second", cid=ID_B, priority=5), cond("First", cid=ID_A, priority=1)),
        [run("First", outcome_id=ID_A), run("Second", outcome_id=ID_B)],
    )
    assert result is not None
    assert [s.title for s in result.slots] == ["First", "Second"]


def test_id_run_and_legacy_run_of_the_same_ending_count_once() -> None:
    result = build_scenario_endings(
        snap(cond("Ashen", cid=ID_A)),
        [run("Ashen", outcome_id=ID_A), run("Ashen")],
    )
    assert result is not None
    assert (result.found_count, result.total_count) == (1, 1)

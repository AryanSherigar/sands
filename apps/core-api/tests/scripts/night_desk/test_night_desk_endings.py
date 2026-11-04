"""The Hum, the four endings (in priority order) and the invariants."""

import pytest
from scripts.night_desk import endings, invariants, minigames, prose

try:
    from mini_eval import evaluate
except ImportError:  # pytest rootdir-relative import fallback
    from tests.scripts.night_desk.mini_eval import evaluate


def _first_matching_ending(state: dict[str, object]) -> str | None:
    ordered = sorted(endings.end_conditions(), key=lambda e: e.priority)
    return next(
        (e.outcome_title for e in ordered if evaluate(e.condition_expression, state)),
        None,
    )


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (
            {
                "sanity": 0,
                "shift_minutes": 200,
                "flags": {"cabin_entered": True},
                "count": {"unsigned": 3},
            },
            "Counted",
        ),
        (
            {
                "sanity": 40,
                "shift_minutes": 420,
                "flags": {"cabin_entered": True},
                "count": {"unsigned": 3},
            },
            "Mr. Orr Is In",
        ),
        (
            {
                "sanity": 40,
                "shift_minutes": 420,
                "flags": {"cabin_entered": False},
                "count": {"unsigned": 2},
            },
            "Visitor",
        ),
        (
            {
                "sanity": 40,
                "shift_minutes": 420,
                "flags": {"cabin_entered": False},
                "count": {"unsigned": 1},
            },
            "Don't Be Late",
        ),
        (
            {
                "sanity": 40,
                "shift_minutes": 400,
                "flags": {"cabin_entered": False},
                "count": {"unsigned": 3},
            },
            None,
        ),
    ],
)
def test_ending_priority(state: dict[str, object], expected: str | None) -> None:
    assert _first_matching_ending(state) == expected


def test_endings_use_the_authored_text_and_none_is_secret() -> None:
    built = endings.end_conditions()
    assert [e.outcome_title for e in built] == [
        "Counted",
        "Mr. Orr Is In",
        "Visitor",
        "Don't Be Late",
    ]
    assert not any(e.is_secret for e in built)
    assert built[0].outcome_text == prose.ENDINGS["counted"].text


def test_only_the_hum_remains() -> None:
    assert [m.label for m in minigames.minigames()] == ["The Hum"]


def test_the_hum_carries_its_whole_consequence() -> None:
    hum = minigames.minigames()[0]
    assert hum.composure_config.texts.win_text == prose.HUM_WIN_TEXT
    assert hum.composure_config.texts.lose_text == prose.HUM_LOSE_TEXT
    assert hum.composure_config.audio_profile == "hum"
    win = {(m.path, m.op): m.value for m in hum.win_mutations}
    assert win[("sanity", "increment")] == 5
    assert win[("rule_status.r8", "set")] == "intact"
    assert win[("flags.hum", "set")] == "done"
    for lost in (hum.lose_mutations, hum.timeout_mutations):
        values = {(m.path, m.op): m.value for m in lost}
        assert values[("sanity", "decrement")] == 25
        assert values[("rule_status.r8", "set")] == "violated"


def test_hum_opens_only_after_the_stairwell_voice() -> None:
    trigger = minigames.minigames()[0].trigger_condition_expression
    assert evaluate(trigger, {"events": {"stairwell": True}, "flags": {"hum": "idle"}})
    assert not evaluate(
        trigger, {"events": {"stairwell": False}, "flags": {"hum": "idle"}}
    )
    assert not evaluate(
        trigger, {"events": {"stairwell": True}, "flags": {"hum": "done"}}
    )


def test_invariants_cap_sanity_clock_and_unsigned_counts() -> None:
    labels = [i.label for i in invariants.invariants()]
    assert labels == ["Sanity cap", "Clock bound", "Unsigned counts"]

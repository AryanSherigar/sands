"""The authored conditions: expressions, mutations, metadata and group order."""

import pytest
from app.models.condition import SENSORY_CUE_IDS
from scripts.night_desk import prose, schema, timeline
from scripts.night_desk.builder import ordered_conditions
from scripts.night_desk.expr import ALWAYS, to_condition
from scripts.night_desk.ids import entity_ref
from scripts.night_desk.validation import _nodes, order_problems

GROUP_LETTERS = "EHVPFDTNA"


@pytest.fixture(scope="module")
def conditions() -> list:
    return [to_condition(cond) for cond in ordered_conditions()]


def _by_label(conditions: list, prefix: str) -> list:
    return [c for c in conditions if c.label.startswith(prefix)]


def _one(conditions: list, prefix: str):
    found = _by_label(conditions, prefix)
    assert len(found) == 1, f"{prefix}: {[c.label for c in found]}"
    return found[0]


def _leaves(expression: dict) -> list[dict]:
    return [
        {k: node[k] for k in ("field", "op", "value")} for node in _nodes(expression)
    ]


def _mutations(condition) -> dict[tuple[str, str], object]:
    return {(m.path, m.op): m.value for m in condition.state_mutations}


def test_group_order_is_enforced(conditions) -> None:
    assert order_problems(conditions) == []
    assert all(c.label[0] in GROUP_LETTERS for c in conditions)


def test_labels_are_unique(conditions) -> None:
    labels = [c.label for c in conditions]
    assert len(labels) == len(set(labels))


def test_volume_is_between_sixty_and_one_hundred_ten(conditions) -> None:
    assert 60 <= len(conditions) <= 110


def test_every_timeline_beat_has_a_timed_condition(conditions) -> None:
    thresholds = {
        leaf["value"]
        for c in conditions
        for leaf in _leaves(c.condition_expression)
        if leaf["field"] == "shift_minutes" and leaf["op"] == ">="
    }
    assert set(timeline.BEATS.values()) - {80} <= thresholds
    assert 80 in thresholds


def test_timed_beats_are_one_shots(conditions) -> None:
    for prefix in ("E01", "E03", "E07", "E09", "E10", "E14", "E15"):
        assert _one(conditions, prefix).is_one_shot


def test_the_clock_advances_twenty_minutes_below_dawn(conditions) -> None:
    advance = _one(conditions, "A01")
    assert _mutations(advance) == {("shift_minutes", "increment"): timeline.STEP}
    assert {"field": "shift_minutes", "op": "<", "value": timeline.SHIFT_END} in (
        _leaves(advance.condition_expression)
    )


def test_visitors_arrive_with_their_chime_and_their_pending_slot(conditions) -> None:
    for number, visitor_id in enumerate(prose.VISITORS, start=1):
        arrival = _one(conditions, f"E{[1, 7, 13][number - 1]:02d}")
        assert _mutations(arrival)[("visit.pending", "set")] == visitor_id
        assert _mutations(arrival)[("visit.present", "set")] == visitor_id
        assert arrival.sensory_cue == "elevator_chime"
        assert prose.VISITORS[visitor_id].told in arrival.narrator_instruction
        assert {"field": "visit.pending", "op": "==", "value": ""} in _leaves(
            arrival.condition_expression
        )


def test_rule_six_hand_follows_the_seed(conditions) -> None:
    leaning = _one(conditions, "E05")
    block = _one(conditions, "E06")
    assert ("rule_status.r6", "set") in _mutations(leaning)
    assert ("rule_status.r6_block", "set") in _mutations(block)
    assert {"field": "seed.false_rule", "op": "==", "value": "r4"} in _leaves(
        leaning.condition_expression
    )
    assert {"field": "seed.false_rule", "op": "==", "value": "r6"} in _leaves(
        block.condition_expression
    )


def test_lamp_out_opens_the_lamp_check(conditions) -> None:
    lamp = _one(conditions, "E09")
    assert _mutations(lamp) == {
        ("cabin.lamp", "set"): "out",
        ("check.lamp", "set"): "pending",
    }
    assert lamp.sensory_cue == "lamp_click"


def test_every_cue_name_is_a_real_cue(conditions) -> None:
    assert {c.sensory_cue for c in conditions if c.sensory_cue} <= set(SENSORY_CUE_IDS)


def test_first_takeover_line_on_first_read_whenever_it_happens(conditions) -> None:
    line_one = _one(conditions, "H10")
    params = line_one.metadata["client_effect"]["params"]
    assert params["text"] == "Get me out of here, Orr"
    assert {"field": "count.reads_after_two", "op": "==", "value": 1} in _leaves(
        line_one.condition_expression
    )
    assert ALWAYS in _leaves(line_one.condition_expression) or {
        "field": "shift_minutes",
        "op": ">=",
        "value": 0,
    } in _leaves(line_one.condition_expression)
    assert _one(conditions, "H11").metadata["client_effect"]["params"]["text"] == (
        "I feel too much"
    )


def test_picking_up_the_phone_plays_the_echo(conditions) -> None:
    echo = _one(conditions, "H12")
    assert echo.metadata["client_effect"]["kind"] == "phone_echo"
    assert echo.narrator_instruction == prose.BEATS["phone_after_pickup"]


def test_unsafe_entry_returns_the_clerk_to_the_corridor(conditions) -> None:
    unsafe = _one(conditions, "H06")
    location = next(
        m for m in unsafe.state_mutations if m.path == "current_location_id"
    )
    assert location.value == entity_ref("east_corridor")
    assert _mutations(unsafe)[("sanity", "decrement")] == 25


def test_safe_entry_puts_the_clerk_in_the_cabin(conditions) -> None:
    safe = _one(conditions, "H05")
    mutations = _mutations(safe)
    assert mutations[("current_location_id", "set")] == entity_ref("cabin_14")
    assert mutations[("flags.cabin_entered", "set")] is True
    assert mutations[("check.lamp", "set")] == ""


def test_lamp_handlers_split_by_seed(conditions) -> None:
    held_true = _one(conditions, "H01")
    held_false = _one(conditions, "H02")
    assert held_true.narrator_instruction == prose.LAMP_OUTCOMES["held_safe"]
    assert held_false.narrator_instruction == prose.LAMP_OUTCOMES["held_unsafe"]
    assert _mutations(held_false)[("sanity", "decrement")] == 15
    assert _mutations(_one(conditions, "H03"))[("sanity", "decrement")] == 10
    assert ("sanity", "decrement") not in _mutations(_one(conditions, "H04"))


def test_a_timed_out_count_counts_as_unsigned(conditions) -> None:
    timeouts = [c for c in conditions if "Count" in c.label and "timed out" in c.label]
    assert len(timeouts) == 3
    for condition in timeouts:
        assert _mutations(condition)[("count.unsigned", "increment")] == 1


def test_visitors_leave_after_three_turns(conditions) -> None:
    departures = [c for c in conditions if "leaves" in c.label]
    assert len(departures) == 3
    for departure in departures:
        assert {"field": "visit.turns_present", "op": ">=", "value": 3} in _leaves(
            departure.condition_expression
        )
        assert _mutations(departure)[("visit.present", "set")] == ""


def test_the_alcove_and_cabin_approach_backstops(conditions) -> None:
    approach = _one(conditions, "P03")
    assert not approach.is_one_shot
    assert approach.narrator_instruction == prose.BEATS["cabin_locked"]
    assert _mutations(approach)[("current_location_id", "set")] == entity_ref(
        "east_corridor"
    )
    assert _by_label(conditions, "P02")


def test_records_visits_count_once_per_visit(conditions) -> None:
    entry = _one(conditions, "P04")
    assert _mutations(entry)[("visited.records_room", "increment")] == 1
    assert {"field": "visited.last", "op": "!=", "value": "records_room"} in _leaves(
        entry.condition_expression
    )


def test_one_fragment_per_act(conditions) -> None:
    slots = {
        m.path
        for c in conditions
        if c.label.startswith("F") and not c.label.startswith("FP")
        for m in c.state_mutations
    }
    assert slots == {"fragments.act1", "fragments.act2", "fragments.act3"}


def test_each_fragment_waits_for_an_empty_slot_and_fires_once(conditions) -> None:
    fragments = [
        c
        for c in conditions
        if c.label.startswith("F") and not c.label.startswith("FP")
    ]
    assert len(fragments) == 6
    for fragment in fragments:
        assert fragment.is_one_shot
        slot = next(m.path for m in fragment.state_mutations)
        assert {"field": slot, "op": "==", "value": ""} in _leaves(
            fragment.condition_expression
        )


def test_poster_carries_the_authored_image(conditions) -> None:
    poster = _one(conditions, "FP")
    assert poster.metadata["authored_image_url"].endswith(
        "night-desk/truefeel-poster.png"
    )
    assert _mutations(poster)[("fragments.poster", "set")] == "shown"
    assert poster.narrator_instruction == prose.FRAGMENT_EVIDENCE["poster"]


def test_drains_total_twelve(conditions) -> None:
    drains = _by_label(conditions, "D")
    assert sum(_mutations(c)[("sanity", "decrement")] for c in drains) == 12


def test_three_act_registers_and_four_tiers(conditions) -> None:
    assert len(_by_label(conditions, "T0")) == 3
    assert len(_by_label(conditions, "T1")) == 4


def test_the_r6_hand_is_a_fact_not_a_directive(conditions) -> None:
    hands = [c for c in conditions if c.label.startswith("T3")]
    assert any(c.narrator_instruction == prose.BEATS["r6_hand_leaning"] for c in hands)
    assert all(c.metadata.get("placement") == "facts" for c in hands)


def test_schema_covers_every_condition_field(conditions) -> None:
    flat = schema.flatten_schema(schema.build_state_schema())
    roots = {"rule_status", "rule_flags", "current_location_id", "player"}
    for condition in conditions:
        for leaf in _leaves(condition.condition_expression):
            field = leaf["field"]
            assert field in flat or field.split(".")[0] in roots, field
        for mutation in condition.state_mutations:
            path = mutation.path
            assert path in flat or path.split(".")[0] in roots, path


def _ambient(conditions: list) -> list:
    return _by_label(conditions, "T4")


def test_every_turn_of_the_night_has_exactly_one_ambient_detail(conditions) -> None:
    from tests.scripts.night_desk.mini_eval import evaluate

    ambient = _ambient(conditions)
    assert len(ambient) == prose.AMBIENT_DECK.__len__()
    for index, line in enumerate(prose.AMBIENT_DECK):
        minute = index * timeline.STEP
        active = [
            c
            for c in ambient
            if evaluate(c.condition_expression, {"shift_minutes": minute})
        ]
        assert len(active) == 1, minute
        assert line in active[0].narrator_instruction
    assert not any(
        evaluate(c.condition_expression, {"shift_minutes": timeline.SHIFT_END})
        for c in ambient
    )


def test_ambient_details_are_directives_with_no_state_effect(conditions) -> None:
    for condition in _ambient(conditions):
        assert not condition.state_mutations
        assert not condition.is_one_shot
        assert condition.metadata.get("placement") != "facts"

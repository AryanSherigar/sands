import pytest
from scripts.night_desk import checks, consequences, prose, sheet_rules


@pytest.fixture(scope="module")
def rule_checks() -> list:
    return checks.rule_checks()


def _check(rule_checks: list, label: str):
    return next(c for c in rule_checks if c.label == label)


def _option(check, option_id: str) -> dict:
    return next(o for o in check.params["options"] if o["id"] == option_id)


def test_two_r6_rows_share_number_six() -> None:
    sixes = [rule for rule in sheet_rules.sheet_rules() if rule.number == 6]
    assert sorted(rule.source_style for rule in sixes) == ["ink", "ink_block"]
    assert all(rule.initial_status == "unrevealed" for rule in sixes)


def test_seven_rules_with_the_v3_hands() -> None:
    rules = {rule.key: rule for rule in sheet_rules.sheet_rules()}
    assert sorted(rules) == ["r1", "r2", "r3", "r4", "r6", "r6_block", "r7", "r8"]
    assert rules["r7"].source_style == "printed"
    assert rules["r8"].source_style == "spoken"
    assert rules["r6"].text == prose.STANDING_INSTRUCTIONS["r6"]
    assert rules["r6_block"].text == prose.STANDING_INSTRUCTIONS["r6"]
    assert [k for k, r in rules.items() if r.initial_status == "intact"] == [
        "r1",
        "r2",
        "r3",
        "r4",
    ]
    assert [k for k, r in rules.items() if r.is_ai_flaggable] == ["r2"]


def test_reading_a_late_count_breaks_r7(rule_checks) -> None:
    read = _option(_check(rule_checks, "Count 2"), "read")
    paths = [m["path"] for m in read["mutations"]]
    assert "rule_status.r7" in paths and "count.reads_after_two" in paths


def test_count_one_has_no_read_option(rule_checks) -> None:
    ids = [o["id"] for o in _check(rule_checks, "Count 1").params["options"]]
    assert ids == ["sign", "leave"]


def test_leaving_a_count_is_counted_as_unsigned(rule_checks) -> None:
    for label in ("Count 1", "Count 2", "Count 3"):
        leave = _option(_check(rule_checks, label), "leave")
        assert {"path": "count.unsigned", "op": "increment", "value": 1} in leave[
            "mutations"
        ]


def test_count_template_reads_the_difference_from_state(rule_checks) -> None:
    template = _check(rule_checks, "Count 1").narrator_instruction_template
    assert "{state:count.difference}" in template
    assert "{result}" in template


def test_every_visitor_told_time_differs_from_the_wall() -> None:
    for visitor, minute in zip(prose.VISITORS.values(), (40, 160, 300), strict=True):
        wall = (23 * 60 + minute) % 1440
        assert visitor.told_minute_of_day != wall


def test_visitor_checks_fire_before_counts_and_the_rest(rule_checks) -> None:
    order = [c.label for c in sorted(rule_checks, key=lambda c: c.priority)]
    assert order[:3] == ["Visitor log 1", "Visitor log 2", "Visitor log 3"]
    assert order[3:6] == ["Count 1", "Count 2", "Count 3"]


def test_wrong_visitor_entry_costs_r1_and_raises_the_difference(rule_checks) -> None:
    visitor = _check(rule_checks, "Visitor log 1")
    paths = [m["path"] for m in visitor.params["wall"]["mutations"]]
    assert "rule_status.r1" in paths and "count.wrong_entries" in paths
    rejected = [m["path"] for m in visitor.params["reject"]["mutations"]]
    assert "count.wrong_entries" in rejected and "rule_status.r1" not in rejected


def test_phone_pickup_is_cardinal_and_lights_line_14(rule_checks) -> None:
    pick_up = _option(_check(rule_checks, "Phone"), "pick_up")
    mutations = {(m["path"], m["op"]): m["value"] for m in pick_up["mutations"]}
    assert mutations[("sanity", "decrement")] == 15
    assert mutations[("flags.line14_lit", "set")] is True
    assert mutations[("rule_status.r3", "set")] == "violated"


def test_lamp_check_leaves_outcomes_to_the_seed_handler(rule_checks) -> None:
    lamp = _check(rule_checks, "Lamp")
    assert all(o["mutations"] == [] for o in lamp.params["options"])
    assert lamp.params["hidden_result"] == "moved"
    assert {o["result"] for o in lamp.params["options"]} == {
        "held_still",
        "moved",
        "entered",
    }


def test_voicemail_and_drawer_are_yes_or_no(rule_checks) -> None:
    assert _option(_check(rule_checks, "Voicemail"), "play")["result"] == "yes"
    assert _option(_check(rule_checks, "Drawer"), "open")["result"] == "yes"
    assert _check(rule_checks, "Drawer").params["timeout_result"] == "no"


def test_consequence_bundles_use_the_v3_amounts() -> None:
    def amount(mutations) -> int:
        return next(m.value for m in mutations if m.path == "sanity")

    assert amount(consequences.soft_violation("r1")) == 10
    assert amount(consequences.cardinal_violation("r3")) == 15
    assert amount(consequences.unsafe_entry()) == 25
    assert amount(consequences.escalation()) == 2

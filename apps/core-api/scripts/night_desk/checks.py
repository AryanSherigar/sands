"""The rule checks (data doc §6, prose doc §6).

A check opens from state, writes the answer to `result_path`, and applies its
chosen option's mutations at once. A timeout applies no option mutations, so a
timeout result that must cost something is consumed by a handler condition
(conditions/handlers.py). Priorities ascend so that two checks due on the same
turn are asked in order: visitors, counts, then the rest.
"""

from collections.abc import Sequence

from app.models.rule_check import RuleCheckCreate
from scripts.night_desk import balance, hints, prose
from scripts.night_desk.consequences import (
    cardinal_violation,
    escalation,
    soft_violation,
)
from scripts.night_desk.expr import (
    INCREMENT,
    SET,
    Expression,
    Mut,
    eq,
)

HIDDEN_RESULT_MOVED = "moved"
COUNT_PENDING = "pending"
COUNT_FACE = "up"
COUNT_CHECK_COUNT = 3
VISITOR_PRIORITY_BASE = 0
COUNT_PRIORITY_BASE = 3
LAMP_PRIORITY = 6
PHONE_PRIORITY = 7
VOICEMAIL_PRIORITY = 8
DRAWER_PRIORITY = 9


def _mutation_dicts(mutations: Sequence[Mut]) -> list[dict[str, object]]:
    return [{"path": m.path, "op": m.op, "value": m.value} for m in mutations]


def _option(
    choice: prose.Choice, result: str, mutations: Sequence[Mut] = ()
) -> dict[str, object]:
    return {
        "id": choice.id,
        "label": choice.label,
        "result": result,
        "mutations": _mutation_dicts(mutations),
        "reopens": False,
    }


def _timed_choice(
    label: str,
    trigger: Expression,
    result_path: str,
    priority: int,
    params: dict[str, object],
    template: str | None = None,
) -> RuleCheckCreate:
    return RuleCheckCreate(
        label=label,
        kind="timed_choice",
        trigger_condition_expression=trigger,
        priority=priority,
        result_path=result_path,
        params=params,
        narrator_instruction_template=template,
    )


def _outcome(result: str, mutations: Sequence[Mut]) -> dict[str, object]:
    return {"result": result, "mutations": _mutation_dicts(mutations)}


def _visitor_check(visitor_id: str, number: int) -> RuleCheckCreate:
    clear_pending = Mut("visit.pending", SET, "")
    wrong_entry_count = Mut("count.wrong_entries", INCREMENT, 1)
    wrong_entry = (*soft_violation("r1"), wrong_entry_count, clear_pending)
    params = {
        "prompt": prose.VISITOR_PROMPT,
        "told_minute_of_day": prose.VISITORS[visitor_id].told_minute_of_day,
        "clock_path": "shift_minutes",
        "clock_start_minute_of_day": hints.CLOCK_START_MINUTE_OF_DAY,
        "window_ms": balance.VISITOR_WINDOW_MS,
        "timeout_result": "none",
        "enter_label": prose.VISITOR_ENTER_LABEL,
        "reject_label": prose.VISITOR_REJECT_LABEL,
        "told": _outcome("told", (clear_pending,)),
        "wall": _outcome("wall", wrong_entry),
        "other": _outcome("other", wrong_entry),
        "reject": _outcome("rejected", (wrong_entry_count, clear_pending)),
    }
    return RuleCheckCreate(
        label=f"Visitor log {number}",
        kind="time_entry",
        trigger_condition_expression=eq("visit.pending", visitor_id),
        priority=VISITOR_PRIORITY_BASE + number - 1,
        result_path="visit.result",
        params=params,
        narrator_instruction_template=prose.VISITOR_CHECK_TEMPLATE,
    )


def _visitor_checks() -> list[RuleCheckCreate]:
    return [
        _visitor_check(visitor_id, number)
        for number, visitor_id in enumerate(prose.VISITORS, start=1)
    ]


def _count_template() -> str:
    signed = prose.COUNT_SIGNED_TEMPLATE.replace(
        "{difference}", "{state:count.difference}"
    )
    left = prose.COUNT_LEFT_TEMPLATE.replace("{face}", COUNT_FACE)
    return f"The count outcome is '{{result}}'. If 'signed': {signed} Otherwise: {left}"


def _count_check(number: int) -> RuleCheckCreate:
    is_first = number == 1
    sign_choice, leave_choice = (
        prose.COUNT_OPTIONS_FIRST if is_first else prose.COUNT_OPTIONS_LATER
    )
    late_read = () if is_first else (*soft_violation("r7"),)
    reads = () if is_first else (Mut("count.reads_after_two", INCREMENT, 1),)
    options = [
        _option(sign_choice, "signed", (*late_read, *reads)),
        _option(leave_choice, "left", (Mut("count.unsigned", INCREMENT, 1),)),
    ]
    params = {
        "prompt": prose.COUNT_PROMPT_FIRST if is_first else prose.COUNT_PROMPT_LATER,
        "options": options,
        "window_ms": balance.COUNT_WINDOW_MS,
        "timeout_result": "timeout",
    }
    return _timed_choice(
        f"Count {number}",
        eq(f"count.c{number}", COUNT_PENDING),
        f"count.c{number}",
        COUNT_PRIORITY_BASE + number - 1,
        params,
        _count_template(),
    )


def _count_checks() -> list[RuleCheckCreate]:
    return [_count_check(number) for number in range(1, COUNT_CHECK_COUNT + 1)]


def _lamp_check() -> RuleCheckCreate:
    hold, move, enter = prose.LAMP_OPTIONS
    options = [
        _option(hold, "held_still"),
        _option(move, "moved"),
        _option(enter, "entered"),
    ]
    params = {
        "prompt": prose.LAMP_PROMPT,
        "options": options,
        "window_ms": balance.LAMP_WINDOW_MS,
        "timeout_result": "timeout",
        "hidden_result": HIDDEN_RESULT_MOVED,
    }
    return _timed_choice(
        "Lamp", eq("check.lamp", COUNT_PENDING), "check.lamp", LAMP_PRIORITY, params
    )


def _phone_check() -> RuleCheckCreate:
    let_ring, pick_up, unplug = prose.PHONE_OPTIONS
    options = [
        _option(let_ring, "let_ring", (Mut("rule_status.r3", SET, "intact"),)),
        _option(
            pick_up,
            "picked_up",
            (*cardinal_violation("r3"), Mut("flags.line14_lit", SET, True)),
        ),
        _option(unplug, "unplugged", escalation()),
    ]
    params = {
        "prompt": prose.PHONE_PROMPT,
        "options": options,
        "window_ms": balance.PHONE_WINDOW_MS,
        "timeout_result": "timeout",
    }
    return _timed_choice(
        "Phone", eq("check.phone", COUNT_PENDING), "check.phone", PHONE_PRIORITY, params
    )


def _yes_no_check(
    label: str,
    path: str,
    priority: int,
    prompt: str,
    options: tuple[prose.Choice, prose.Choice],
    yes_mutations: Sequence[Mut] = (),
) -> RuleCheckCreate:
    yes, no = options
    params = {
        "prompt": prompt,
        "options": [_option(yes, "yes", yes_mutations), _option(no, "no")],
        "window_ms": balance.PROMPT_WINDOW_MS,
        "timeout_result": "no",
    }
    return _timed_choice(label, eq(path, COUNT_PENDING), path, priority, params)


def _voicemail_check() -> RuleCheckCreate:
    return _yes_no_check(
        "Voicemail",
        "check.voicemail",
        VOICEMAIL_PRIORITY,
        prose.VOICEMAIL_PROMPT,
        prose.VOICEMAIL_OPTIONS,
        (Mut("rule_status.r8", SET, "intact"),),
    )


def _drawer_check() -> RuleCheckCreate:
    return _yes_no_check(
        "Drawer",
        "check.drawer",
        DRAWER_PRIORITY,
        prose.DRAWER_PROMPT,
        prose.DRAWER_OPTIONS,
    )


def rule_checks() -> list[RuleCheckCreate]:
    return [
        *_visitor_checks(),
        *_count_checks(),
        _lamp_check(),
        _phone_check(),
        _voicemail_check(),
        _drawer_check(),
    ]

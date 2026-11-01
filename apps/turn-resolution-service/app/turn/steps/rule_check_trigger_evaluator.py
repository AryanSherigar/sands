"""Opens rule checks (timed prompts) from end-of-turn state.

Runs after the minigame trigger, before state_writer (pipeline.py is the sole
sequencer). A check fires on a rising edge of its trigger: true now and not true
at the end of the previous turn. Fired checks queue, and one opens at a time.
Results, mutations and timeout outcomes stay in the snapshot; only the public
prompt is stamped into state (docs/specs/rules-horror-engine/
rule-checks-tool.spec.md §2.3-2.4).
"""

import time
import uuid
from dataclasses import dataclass, field

import structlog
from app.config import settings
from app.models.check_event import RuleCheckEventPayload
from app.turn.expression_evaluator import evaluate
from app.turn.rule_check_payload import build_event_payload
from app.turn.tools import is_enabled

logger = structlog.get_logger()

EVENT_RULE_CHECK_OPENED = "rule_check_opened"
EVENT_RULE_CHECK_EVALUATION_ERROR = "rule_check_evaluation_error"
EVENT_RULE_CHECK_QUEUE_OVERFLOW = "rule_check_queue_overflow"
EVENT_RULE_CHECK_QUEUE_STALE = "rule_check_queue_stale_entry"
TOOL_KEY = "rule_checks"
STATE_KEY_PENDING_CHECK = "_pending_check"
STATE_KEY_PENDING_MINIGAME = "_pending_minigame"
STATE_KEY_CHECK_EDGES = "_check_edges"
STATE_KEY_CHECK_QUEUE = "_check_queue"
STATE_KEY_CHECK_REOPENS = "_check_reopens"


@dataclass
class RuleCheckTriggerResult:
    mutated_paths: set[str] = field(default_factory=set)
    payload: RuleCheckEventPayload | None = None


def current_time_ms() -> int:
    return time.time_ns() // 1_000_000


def evaluate_rule_check_triggers(
    scenario_snapshot: dict[str, object],
    working_state: dict[str, object],
    *,
    participant_count: int,
    can_open: bool,
    now_ms: int,
) -> RuleCheckTriggerResult:
    """Updates `working_state` in place (edges, queue, and `_pending_check` when
    a check opens). `can_open` is False when a minigame or a dice check claimed
    this turn; the fired check then waits in the queue."""
    if participant_count > 1 or not is_enabled(scenario_snapshot, TOOL_KEY):
        return RuleCheckTriggerResult()
    checks = _checks_by_priority(scenario_snapshot)
    result = RuleCheckTriggerResult()
    _record_edges_and_queue(checks, working_state, result)
    is_free = (
        can_open
        and not working_state.get(STATE_KEY_PENDING_CHECK)
        and not working_state.get(STATE_KEY_PENDING_MINIGAME)
    )
    if is_free:
        _open_next_queued_check(checks, working_state, now_ms, result)
    return result


def _checks_by_priority(
    scenario_snapshot: dict[str, object],
) -> list[dict[str, object]]:
    listed = scenario_snapshot.get("rule_checks")
    checks = (
        [c for c in listed if isinstance(c, dict)] if isinstance(listed, list) else []
    )
    return sorted(checks, key=lambda check: _priority_of(check))


def _priority_of(check: dict[str, object]) -> int:
    priority = check.get("priority")
    return priority if isinstance(priority, int) else 0


def _try_evaluate(check: dict[str, object], state: dict[str, object]) -> bool:
    try:
        return evaluate(check.get("trigger_condition_expression"), state)
    except Exception:
        logger.warning(
            EVENT_RULE_CHECK_EVALUATION_ERROR,
            check_id=check.get("check_id"),
            exc_info=True,
        )
        return False


def _take_reopen_count(
    state: dict[str, object], definition_id: str, result: RuleCheckTriggerResult
) -> int:
    reopens = state.get(STATE_KEY_CHECK_REOPENS)
    if not isinstance(reopens, dict) or definition_id not in reopens:
        return 0
    remaining = {k: v for k, v in reopens.items() if k != definition_id}
    state[STATE_KEY_CHECK_REOPENS] = remaining
    result.mutated_paths.add(STATE_KEY_CHECK_REOPENS)
    count = reopens[definition_id]
    return count if isinstance(count, int) else 0


def _string_list(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _record_edges_and_queue(
    checks: list[dict[str, object]],
    state: dict[str, object],
    result: RuleCheckTriggerResult,
) -> None:
    previous_edges = set(_string_list(state.get(STATE_KEY_CHECK_EDGES)))
    queue = _string_list(state.get(STATE_KEY_CHECK_QUEUE))
    pending_def_id = _pending_definition_id(state)
    current_edges: list[str] = []
    for check in checks:
        check_id = str(check.get("check_id"))
        if not _try_evaluate(check, state):
            continue
        current_edges.append(check_id)
        is_waiting = check_id in queue or check_id == pending_def_id
        if check_id not in previous_edges and not is_waiting:
            queue = _enqueue(queue, check_id)
    _write_if_changed(state, STATE_KEY_CHECK_EDGES, current_edges, result)
    _write_if_changed(state, STATE_KEY_CHECK_QUEUE, queue, result)


def _pending_definition_id(state: dict[str, object]) -> str | None:
    pending = state.get(STATE_KEY_PENDING_CHECK)
    if isinstance(pending, dict) and pending.get("check_def_id") is not None:
        return str(pending["check_def_id"])
    return None


def _enqueue(queue: list[str], check_id: str) -> list[str]:
    if len(queue) >= settings.rule_check_queue_max:
        logger.warning(EVENT_RULE_CHECK_QUEUE_OVERFLOW, check_id=check_id)
        return queue
    return [*queue, check_id]


def _write_if_changed(
    state: dict[str, object],
    key: str,
    value: list[str],
    result: RuleCheckTriggerResult,
) -> None:
    if _string_list(state.get(key)) == value:
        return
    state[key] = value
    result.mutated_paths.add(key)


def _open_next_queued_check(
    checks: list[dict[str, object]],
    state: dict[str, object],
    now_ms: int,
    result: RuleCheckTriggerResult,
) -> None:
    definitions = {str(check.get("check_id")): check for check in checks}
    queue = _string_list(state.get(STATE_KEY_CHECK_QUEUE))
    while queue:
        head = queue.pop(0)
        definition = definitions.get(head)
        if definition is None:
            logger.warning(EVENT_RULE_CHECK_QUEUE_STALE, check_id=head)
            continue
        state[STATE_KEY_CHECK_QUEUE] = queue
        result.mutated_paths |= {STATE_KEY_CHECK_QUEUE, STATE_KEY_PENDING_CHECK}
        reopen_count = _take_reopen_count(state, head, result)
        result.payload = _stamp_pending_check(state, definition, now_ms, reopen_count)
        return
    _write_if_changed(state, STATE_KEY_CHECK_QUEUE, queue, result)


def _stamp_pending_check(
    state: dict[str, object],
    definition: dict[str, object],
    now_ms: int,
    reopen_count: int,
) -> RuleCheckEventPayload:
    payload = build_event_payload(
        definition,
        check_id=str(uuid.uuid4()),
        now_ms=now_ms,
        reopen_count=reopen_count,
        state=state,
    )
    state[STATE_KEY_PENDING_CHECK] = {
        **payload.model_dump(exclude={"server_time_ms"}),
        "check_def_id": str(definition.get("check_id")),
        "resolved": None,
    }
    logger.info(EVENT_RULE_CHECK_OPENED, check_def_id=definition.get("check_id"))
    return payload
